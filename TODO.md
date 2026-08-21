# TODO

- [x] Diagnosed CI failure: 2 transient edge-tts "No audio was received"
      errors (voice=ru-RU-DmitryNeural) caused batch.py to sys.exit(1),
      which aborted the job before the release/publish steps ran.
- [x] Added retry (3 attempts, backoff) to tts_client.synthesize().
- [x] Unbuffered batch.py stdout/stderr so live failures are visible
      during the run, not just at the end.
- [ ] Not done: no test run against real edge-tts endpoint (network
      disabled in this environment) — verify by re-running the
      GitHub Actions workflow.
- [x] 2nd log (86226190571): retry helped but 1/3200 items still failed
      (ru-RU-DmitryNeural, transient) -> still exit(1) -> publish skipped.
- [x] Raised RETRY_ATTEMPTS 3->5, backoff 2.0->3.0 in tts_client.py.
- [x] batch.py now retries all failed items again in a 2nd pass after
      the full run, then only sys.exit(1) if the remaining failure
      rate exceeds --max-failure-rate (default 2%). Below that, it
      logs the failures to stderr but exits 0 so catalog.json + the
      successful .abv files still get zipped/published; the missing
      phrase/lang/gender entries are just absent from catalog.json.
- [ ] Not tested against real edge-tts endpoint (network disabled
      here) — verify by re-running the workflow.

- [x] Bootstrap temporary Avasho session and CSRF automatically from the gateway endpoint so only AVASHO_GATEWAY_TOKEN remains a required repository secret.
- [x] Analyze the new Avasho bootstrap failure and correct the actual session or CSRF handshake required by the service.
- [x] Diagnose and fix the latest Avasho voice-builder failure from the uploaded workflow log.
- [x] Diagnose and fix the newly uploaded Avasho voice-builder workflow failure.
