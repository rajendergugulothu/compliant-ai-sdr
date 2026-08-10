# Compliant AI SDR — common commands
# Mock LLM + fake HubSpot by default (no key/account needed).
# Add ANTHROPIC_API_KEY for the real judge+agent, SDR_HUBSPOT_TOKEN for a real
# HubSpot sandbox, and SDR_ENV=prod for fail-closed behavior.

.PHONY: examples pipeline redteam metrics cases suite prod-demo demo clean

examples:    ## Step 1: compliance harness on example emails
	python -m sdr_eval.run

pipeline:    ## end-to-end draft -> gate -> HubSpot -> dry-run email / escalate
	python -m sdr_agent.pipeline

redteam:     ## agentic red-team: attack the full loop, print attack-success rate
	python -m sdr_agent.redteam

metrics:     ## loop metrics (approval/escalation/auto-fix) from the last run
	python -m sdr_agent.metrics

cases:       ## (re)generate the labeled evaluation dataset
	python -m eval_suite.generate

suite: cases ## run the evaluation suite (catch rate, FPR, latency, cost)
	python -m eval_suite.run

prod-demo:   ## show fail-closed: judge unavailable -> everything escalates
	SDR_ENV=prod python -m sdr_agent.pipeline

demo: pipeline suite metrics   ## the full story end to end

clean:
	rm -rf runs eval_suite/results.json __pycache__ */__pycache__ */*/__pycache__
