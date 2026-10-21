include ../config.mk
# Audit of the name-based links to persons/ (ltlod:matchMethod): a reproducible, stratified
# sample for human review, and the precision it implies. Reads the committed TriG (run the
# domains first); `sample` never overwrites review files that already hold verdicts.
#
#   make -C etl/audit sample   # reviews/*.csv: fill in verdict (ok / wrong / unsure) + note
#   make -C etl/audit score    # precision per link type and method, Wilson 95 % interval

PER_STRATUM ?= 50
SEED ?= 2026

.PHONY: sample score
sample:
	uv run --project ../tools ltlod-audit sample --datasets ../../datasets/current --base $(BASE) \
		--per-stratum $(PER_STRATUM) --seed $(SEED) --out reviews

score:
	uv run --project ../tools ltlod-audit score --reviews reviews
