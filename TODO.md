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
- [ ] Optional: consider a --max-failures / --allow-failures flag on
      batch.py if you want partial builds to still publish instead of
      failing the whole job.
