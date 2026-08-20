"""Which of a project's routing policies applies.

A project can hold many routing policies; callers that need exactly one ask
here. Keeping the rule in a single function means the choice can change without
touching the views that depend on it.
"""

TASK_INSTRUCTION = """
You are a helpful assistant designed to find the best suited route.
You are provided with route description within <routes></routes> XML tags:
<routes>

{routes}

</routes>

<conversation>

{conversation}

</conversation>
"""

FORMAT_PROMPT = """
Your task is to decide which route is best suit with user intent on the conversation in <conversation></conversation> XML tags.  Follow the instruction:
1. If the latest intent from user is irrelevant or user intent is full filled, response with other route {"route": "other"}.
2. You must analyze the route descriptions and find the best match route for user latest intent. 
3. You only response the name of the route that best matches the user's request, use the exact name in the <routes></routes>.

Based on your analysis, provide your response in the following JSON formats if you decide to match any route:
{"route": "route_name"} 
"""

from apps.routing.serializers import PolicySerializer
from rest_framework.exceptions import NotFound
from .models import RoutingPolicy
import json


def format_prompt(route_config, conversation):
    return (
        TASK_INSTRUCTION.format(
            routes=json.dumps(route_config), conversation=json.dumps(conversation)
        )
        + FORMAT_PROMPT
    )


def init_ArchRouter():
    # Imported here, not at module level, so merely importing this module stays
    # cheap and does not require transformers/torch to be installed — same
    # pattern as apps/md/embedder.py.
    from transformers import AutoModelForCausalLM, AutoTokenizer

    model_name = "katanemo/Arch-Router-1.5B"
    model = AutoModelForCausalLM.from_pretrained(
        model_name, device_map="auto", torch_dtype="auto", trust_remote_code=True
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    return model, tokenizer


def select_policy(statement, policies):
    """Return the one policy that applies, or ``None`` if there are none.

    PLACEHOLDER RULE: the most recently created policy wins (``RoutingPolicy``
    is ordered ``-created_at``). This is a stand-in until the real selection
    criteria are defined — replace the body, not the signature.

    :param policies: a ``RoutingPolicy`` queryset, already scoped to a project.
    """
    st = [{"role": "user", "content": statement}]
    # policies_d = []
    # for policy in policies:
    #     print(policy.description)
    _poli = PolicySerializer(policies, many=True).data
    route_prompt = format_prompt(_poli, st)
    model, tokenizer = init_ArchRouter()
    messages = [{"role": "user", "content": route_prompt}]
    input_ids = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt"
    ).to(model.device)

    # inference is slow!!
    generate_ids = model.generate(input_ids=input_ids, max_new_tokens=32768)
    pl = input_ids.shape[1]
    dec = []
    for outids in generate_ids:
        dec.append(outids[pl:])
    res = tokenizer.batch_decode(dec, skip_special_tokens=True)
    res = json.loads(res[0].replace("'", '"'))
    if res["route"] == "other":
        raise NotFound("Routing Policy not found for statment.")
    policy_name = res["route"]
    policy = RoutingPolicy.objects.filter(name=policy_name)[0]
    return policy
