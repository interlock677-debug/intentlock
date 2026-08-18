from app.domain.services.intent_evaluator import IntentEvaluatorService
from app.domain.models.intent import AgentActionDAG

evaluator = IntentEvaluatorService()

# Branch 84->91: sqlglot parses successfully but sql_type not in destructive set
# This happens with SELECT statements
intent = AgentActionDAG(
    agent_id='a',
    user_prompt='just a query',
    reasoning_step='step',
    proposed_tool='sql_query',
    tool_arguments={'query': 'SELECT * FROM table'}
)
result = evaluator._inspect_destructive_sql(intent)
print(f'SELECT sqlglot parse result: {result}')

# Branch at 133->128 in _extract_transfer_amount: $ in value but no digit following
test_cases = [
    {'note': '$abc'},  # $ but no digit
    {'note': 'cost $'},  # $ at end
    {'note': 'cost $ '},  # $ with space after
]
for args in test_cases:
    intent3 = AgentActionDAG(
        agent_id='a',
        user_prompt='transfer',
        reasoning_step='step',
        proposed_tool='transfer_funds',
        tool_arguments=args
    )
    result3 = evaluator.evaluate(intent3)
    print(f'Arguments {args} -> is_valid={result3.is_valid}, reason={result3.reason}')

# Also test transfer with amount exceeding limit
intent4 = AgentActionDAG(
    agent_id='a',
    user_prompt='Send payment up to $100',
    reasoning_step='Send',
    proposed_tool='transfer_funds',
    tool_arguments={'note': 'the cost is $400'},
)
result4 = evaluator.evaluate(intent4)
print(f'Transfer over limit result: is_valid={result4.is_valid}, reason={result4.reason}')