# H-01 reproduction

Stage2 uses `H01_HUMAN_DECISION_V1` and `scenarios/H-01.yaml`. Use clean feature source checkouts
containing Spec006 changes for both repositories. Runtime dependencies may come from existing venvs;
never copy .env. Keep state outside both source trees. This wrapper does not start a Run by itself.

```powershell
python -m scripts.h01_local up --instance h01 --whyyou-repo <clean-whyyou-path> --whyyou-python <whyyou-python> --state-root <outside-state-root> --pg-port 15737 --aws-port 14770 --api-port 18088
python -m scripts.h01_local cli --instance h01 --state-root <outside-state-root> -- preflight H-01 --profile H01_HUMAN_DECISION_V1 --target whyyou-local --json
python -m scripts.h01_local cli --instance h01 --state-root <outside-state-root> -- run H-01 --profile H01_HUMAN_DECISION_V1 --target whyyou-local --label h01-local --json
python -m scripts.h01_local cli --instance h01 --state-root <outside-state-root> -- verify <run-id> --json
python -m scripts.h01_local cli --instance h01 --state-root <outside-state-root> -- show <run-id> --json
python -m scripts.h01_local cli --instance h01 --state-root <outside-state-root> -- retest <parent-id> --target whyyou-local --label h01-child --json
python -m scripts.h01_local stop --instance h01 --state-root <outside-state-root>
```

Inspect READY before Run. Run owns15 applicants/invitations and finally removes its data; a
restore failure blocks another Run. Verify18/17/15-file historical contracts separately from
target PASS. Do not edit old bundles. If the portable stop races an already-exited child,
recheck the recorded creation times and retry; never terminate unrelated local servers.
Actual source identities and limitations: actual-closure.md. Source checkpoints are local
validation commits, not remotely published SHAs. Browser result view is read-only.

## Historical stage1 preparation check

Use `fixes-and-remaining-work` in both repositories. No .env or running service is needed.

```powershell
.venv/Scripts/python.exe -m scripts.h01_prepare --preparation-id 013933f5-ef3b-43f7-a2f7-8c474be05805
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/unit/test_h01_preparation.py tests/contract/test_h01_adapter.py tests/integration/test_h01_preparation_driver.py
# In WhyYou:
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider backend/tests/unit/runtime/test_controlproof_h01.py
```

Expected preparation output: H-01, stage1, actual_status NOT_RUN; five cases and canonical scoped
IDs; no HTTP/DB call, official Run, sealed evidence, stored READY or catalog change.
Automatic fake fixtures/SQLite helper tests are not a WhyYou actual outcome.

Actual binding and source/service preparation must follow contracts/preparation.md stage2 gates.
There is no supported `engine.cli run H-01` command/profile from this preparation alone.
Do not reuse company credentials as AI/SYSTEM identities. Keep existing untracked runtime probes.
