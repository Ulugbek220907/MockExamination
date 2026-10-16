import json

with open("content/reading/book_34_tests.json", "r", encoding="utf-8") as f:
    tests = json.load(f)

print(f"Total tests: {len(tests)}")
for i, t in enumerate(tests):
    tid = t.get("id")
    title = t.get("title")
    passages = t.get("passages", [])
    total_q = sum(len(g.get("questions", [])) for p in passages for g in p.get("groups", []))
    q_nums = [q.get("number") for p in passages for g in p.get("groups", []) for q in g.get("questions", [])]
    expected_nums = list(range(1, 41))
    missing_nums = set(expected_nums) - set(q_nums)
    dup_nums = [x for x in q_nums if q_nums.count(x) > 1]
    
    # Check answers
    no_answer = [q.get("number") for p in passages for g in p.get("groups", []) for q in g.get("questions", []) if not q.get("answer")]
    
    if total_q != 40 or missing_nums or dup_nums or no_answer or len(passages) != 3:
        print(f"Issue in Test {i+1} ({tid}): {len(passages)} passages, {total_q} questions, missing={missing_nums}, dups={set(dup_nums)}, no_answer={no_answer}")
    else:
        # Check passage titles and content lengths
        short_passages = [p.get("passageNumber") for p in passages if len(p.get("text", "")) < 200]
        if short_passages:
            print(f"Warning in Test {i+1} ({tid}): short passages: {short_passages}")

print("Done checking all 34 tests.")
