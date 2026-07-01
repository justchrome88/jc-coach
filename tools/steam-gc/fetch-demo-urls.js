#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const SteamTotp = require('steam-totp');
const SteamUser = require('steam-user');
const GlobalOffensive = require('globaloffensive');

const timeoutMs = Number(process.env.STEAM_BOT_TIMEOUT_MS || '45000');
const credentialDir = process.env.STEAM_BOT_CREDENTIAL_DIR || path.resolve(__dirname, '../../data/steam_bot_credentials');
const refreshTokenPath = path.join(credentialDir, 'refresh-token');

function readStdin() {
  return new Promise((resolve) => {
    let input = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => {
      input += chunk;
    });
    process.stdin.on('end', () => resolve(input));
  });
}

function finish(payload, exitCode = 0) {
  console.log(JSON.stringify(payload));
  process.exit(exitCode);
}

function fail(code, message, details) {
  finish({ok: false, code, error: message, details}, 1);
}

function extractDemoUrl(match) {
  const roundstats = match && match.roundstatsall;
  if (!Array.isArray(roundstats) || !roundstats.length) return null;
  const value = roundstats[roundstats.length - 1] && roundstats[roundstats.length - 1].map;
  return typeof value === 'string' && value.includes('.dem') ? value : null;
}

function logOnDetails() {
  fs.mkdirSync(credentialDir, {recursive: true, mode: 0o700});
  const envToken = process.env.STEAM_BOT_REFRESH_TOKEN || '';
  const fileToken = fs.existsSync(refreshTokenPath) ? fs.readFileSync(refreshTokenPath, 'utf8').trim() : '';
  const refreshToken = envToken.trim() || fileToken;
  if (refreshToken) {
    return {refreshToken, machineName: 'jc-coach-steam-bot'};
  }

  const accountName = process.env.STEAM_BOT_USERNAME || '';
  const password = process.env.STEAM_BOT_PASSWORD || '';
  if (!accountName || !password) {
    fail('missing_bot_credentials', 'STEAM_BOT_USERNAME/STEAM_BOT_PASSWORD or STEAM_BOT_REFRESH_TOKEN is required.');
  }
  const details = {accountName, password, machineName: 'jc-coach-steam-bot'};
  const sharedSecret = process.env.STEAM_BOT_SHARED_SECRET || '';
  const twoFactorCode = process.env.STEAM_BOT_TWO_FACTOR_CODE || '';
  if (sharedSecret) {
    details.twoFactorCode = SteamTotp.getAuthCode(sharedSecret);
  } else if (twoFactorCode) {
    details.twoFactorCode = twoFactorCode;
  }
  return details;
}

(async () => {
  let request;
  try {
    request = JSON.parse(await readStdin());
  } catch (err) {
    fail('invalid_json', 'Expected JSON on stdin.', err.message);
  }
  const shareCodes = Array.from(new Set((request.share_codes || request.shareCodes || []).map((code) => String(code).trim()).filter(Boolean)));
  if (!shareCodes.length) {
    finish({ok: true, results: []});
    return;
  }

  const client = new SteamUser({dataDirectory: credentialDir, autoRelogin: false});
  const csgo = new GlobalOffensive(client);
  const pending = new Map();
  const results = new Map(shareCodes.map((shareCode) => [shareCode, {share_code: shareCode, ok: false}]));
  const stages = [];
  let completed = false;

  function mark(stage, details) {
    stages.push({stage, details, at: new Date().toISOString()});
  }

  function done(payload, exitCode = 0) {
    if (completed) return;
    completed = true;
    try {
      client.gamesPlayed([]);
      client.logOff();
    } catch (_err) {
      // Best-effort shutdown before process exit.
    }
    finish(payload, exitCode);
  }

  const timeout = setTimeout(() => {
    for (const [shareCode, entry] of results.entries()) {
      if (!entry.ok && !entry.error) {
        entry.code = 'timeout';
        entry.error = 'Timed out waiting for Steam Game Coordinator response.';
      }
    }
    done({ok: false, code: 'timeout', stages, results: Array.from(results.values())}, 1);
  }, timeoutMs * Math.max(2, shareCodes.length + 1));

  client.on('refreshToken', (token) => {
    fs.writeFileSync(refreshTokenPath, token, {mode: 0o600});
  });

  client.on('steamGuard', (domain, callback, lastCodeWrong) => {
    mark('steam_guard', {guard_type: domain ? 'email' : 'mobile', email_domain: domain || null, last_code_wrong: !!lastCodeWrong});
    const code = process.env.STEAM_BOT_TWO_FACTOR_CODE || '';
    if (code && !lastCodeWrong) {
      callback(code);
      return;
    }
    clearTimeout(timeout);
    done(
      {
        ok: false,
        code: 'steam_guard_required',
        guard_type: domain ? 'email' : 'mobile',
        email_domain: domain || null,
        error: 'Steam bot needs STEAM_BOT_SHARED_SECRET, STEAM_BOT_TWO_FACTOR_CODE, or STEAM_BOT_REFRESH_TOKEN.',
      },
      1,
    );
  });

  client.on('error', (err) => {
    clearTimeout(timeout);
    done({ok: false, code: 'steam_error', error: err.message, eresult: err.eresult, stages}, 1);
  });

  client.on('loggedOn', async () => {
    mark('logged_on', {steam_id: client.steamID ? client.steamID.toString() : null});
    client.setPersona(SteamUser.EPersonaState.Online);
    try {
      const license = await client.requestFreeLicense([730]);
      mark('free_license_requested', license);
    } catch (err) {
      mark('free_license_error', {message: err.message, eresult: err.eresult});
    }
    client.gamesPlayed(730, true);
  });

  client.on('appLaunched', (appId) => {
    mark('app_launched', {app_id: appId});
  });

  csgo.on('debug', (message) => {
    mark('csgo_debug', {message});
  });

  csgo.on('disconnectedFromGC', (reason) => {
    mark('disconnected_from_gc', {reason});
  });

  csgo.on('connectedToGC', () => {
    mark('connected_to_gc');
    let index = 0;
    const requestNext = () => {
      if (index >= shareCodes.length) {
        if (!pending.size) {
          clearTimeout(timeout);
          done({ok: true, stages, results: Array.from(results.values())});
        }
        return;
      }
      const shareCode = shareCodes[index++];
      const responseTimer = setTimeout(() => {
        mark('match_timeout', {share_code: shareCode});
        pending.delete(shareCode);
        results.set(shareCode, {
          share_code: shareCode,
          ok: false,
          code: 'match_timeout',
          error: 'Timed out waiting for match metadata.',
        });
        requestNext();
      }, timeoutMs);
      pending.set(shareCode, {timer: responseTimer, requestNext});
      try {
        mark('request_game', {share_code: shareCode});
        csgo.requestGame(shareCode);
      } catch (err) {
        clearTimeout(responseTimer);
        pending.delete(shareCode);
        results.set(shareCode, {share_code: shareCode, ok: false, code: 'request_failed', error: err.message});
        requestNext();
      }
    };
    requestNext();
  });

  csgo.on('matchList', (matches) => {
    mark('match_list', {matches: (matches || []).length});
    for (const match of matches || []) {
      for (const [shareCode, pendingEntry] of pending.entries()) {
        const current = results.get(shareCode);
        if (current && current.ok) continue;
        const url = extractDemoUrl(match);
        if (!url) continue;
        clearTimeout(pendingEntry.timer);
        pending.delete(shareCode);
        results.set(shareCode, {
          share_code: shareCode,
          ok: true,
          match_id: match.matchid,
          match_time: match.matchtime,
          demo_url: url,
        });
        pendingEntry.requestNext();
        break;
      }
    }
  });

  client.logOn(logOnDetails());
})();
