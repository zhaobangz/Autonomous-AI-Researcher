def agent_loop(task):

    plan = planner.generate_plan(task)

    context = []

    for step in plan:

        if step == "search_papers":
            papers = arxiv_search(task)

        elif step == "summarize":
            summary = researcher.summarize(papers)

        elif step == "write_experiment":
            code = coder.generate_code(summary)

        elif step == "run_experiment":
            results = execute_code(code)

        elif step == "analyze":
            analysis = critic.review(results)

        context.append(analysis)

    report = generate_report(context)

    return report