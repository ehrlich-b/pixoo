SCRIPT := mandelbrot_zoom.py
LOG    := /tmp/mandelbrot_run.log
ARGS   := --loop --doubles=25 --doublec=25 20
IP     := 192.168.4.111

.PHONY: restart stop logs status watch on off

restart: stop on
	@nohup python3 $(SCRIPT) $(ARGS) > $(LOG) 2>&1 &
	@sleep 1
	@echo "started: python3 $(SCRIPT) $(ARGS) (log: $(LOG))"
	@head -5 $(LOG) 2>/dev/null || true

stop:
	@pkill -f "$(SCRIPT)" 2>/dev/null || true
	@sleep 0.3

logs:
	@tail -f $(LOG)

status:
	@pgrep -af "$(SCRIPT)" || echo "not running"

on:
	@curl -s -X POST http://$(IP)/post -H "Content-Type: application/json" \
		-d '{"Command":"Channel/OnOffScreen","OnOff":1}' >/dev/null

off: stop
	@curl -s -X POST http://$(IP)/post -H "Content-Type: application/json" \
		-d '{"Command":"Channel/OnOffScreen","OnOff":0}' >/dev/null
	@echo "screen off; process killed"

watch:
	@command -v fswatch >/dev/null || { echo "install fswatch: brew install fswatch"; exit 1; }
	@$(MAKE) restart
	@echo "watching $(SCRIPT) — save to auto-restart (ctrl-c to exit)"
	@fswatch -o $(SCRIPT) | while read _; do echo "--- change detected ---"; $(MAKE) restart; done
