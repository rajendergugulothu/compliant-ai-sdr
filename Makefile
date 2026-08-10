# Compliant AI SDR — common commands
# Everything runs in mock mode by default (no key needed). Add ANTHROPIC_API_KEY
# to your environment to enable the real LLM judge + agent.

.PHONY: eval pipeline redteam metrics demo clean

eval:        ## run the Step-1 compliance harness on example emails
	python -m sdr_eval.run

pipeline:    ## run the end-to-end draft -> gate -> send/escalate pipeline
	python -m sdr_agent.pipeline

redteam:     ## attack the pipeline and print attack-success-rate
	python -m sdr_agent.redteam

metrics:     ## summarize the last pipeline run
	python -m sdr_agent.metrics

demo: pipeline redteam metrics   ## run the whole thing end to end

clean:
	rm -rf runs __pycache__ */__pycache__ */*/__pycache__
