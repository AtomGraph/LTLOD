Synthetic fixture for `make -C etl/sodra test`. This is NOT Sodra data: the JAR codes
(1000000xx), names and figures are invented, and the build writes into `cache/` only.
The header mirrors the published `monthly-{yyyy}.csv` layout as far as it is known
(see the PR notes: the real header must be confirmed on the first harvest).

The rows exercise a decimal comma, a second insurer row for one JAR code and month
(merged), a municipality given by AR code, one that does not resolve, an empty wage, a
row without a JAR code (skipped) and the month window (`SODRA_MONTHS`).
