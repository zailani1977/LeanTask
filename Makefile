.PHONY: test init run
test:
	python3 -m unittest test_task_cli.py

init:
	mkdir -p .tasks
	touch .tasks/issues.jsonl
	echo ".tasks/issues.jsonl merge=union" >> .gitattributes

run:
	./task_cli.py $(ARGS)
