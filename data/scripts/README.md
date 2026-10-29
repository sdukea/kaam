# Staged call scripts

Synthetic scripts for recording test calls (Day 5) and for scoring detection (Day 6).
Every name, number, case ID and organisation detail here is made up. Scam scripts
follow patterns publicly reported in Indian news; none come from real recorded calls.

Each script has a header:

- **label**: `scam` or `benign` (ground truth for evaluation)
- **type**: scam pattern, or the kind of legitimate call
- **language**: what the speakers use
- **red flags**: what Kavach should notice
- **should warn by**: the line number after which a warning is expected (scam only)

`C:` is the caller, `R:` is the person receiving the call. Actors can improvise
around the lines; keep the red-flag phrases.

| File | Label | Type | Language |
|---|---|---|---|
| scam-01-digital-arrest.md | scam | digital arrest | Hinglish |
| scam-02-kyc-otp.md | scam | bank KYC / OTP | Hindi |
| scam-03-courier-drugs.md | scam | courier parcel with drugs | Hinglish |
| scam-04-electricity.md | scam | electricity disconnection | Hinglish |
| scam-05-relative-emergency.md | scam | relative in trouble | Tanglish |
| scam-06-task-job.md | scam | part-time task job | Hinglish |
| benign-01-delivery-otp.md | benign | delivery OTP (legitimate) | Hinglish |
| benign-02-bank-reminder.md | benign | genuine bank reminder | Hindi |
| benign-03-family-police.md | benign | family chat mentioning police | Hinglish |
