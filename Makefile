# talks/Makefile — 公開用リポジトリの手入れ (取り決めは PUBLISHING.md)
UV ?= uv

.PHONY: help index check
help:
	@echo "make index   各講演の meta.yml から index.html を作り直す"
	@echo "make check   公開済みの全講演を tools/check.py で調べ直す"

index:
	$(UV) run --quiet --script tools/build-index.py .

check:
	@dirs=`ls -d */meta.yml 2>/dev/null | sed 's|/meta.yml||'`; \
	if [ -z "$$dirs" ]; then echo "講演はまだない"; else $(UV) run --quiet --script tools/check.py $$dirs; fi
