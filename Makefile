.PHONY: test init run
test:
	python -m unittest test_task_cli.py

init:
	python task_cli.py init

run:
	python task_cli.py $(ARGS)
