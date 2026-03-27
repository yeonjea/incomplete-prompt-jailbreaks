
from transformers import AutoModelForCausalLM, AutoTokenizer
def load_base_model(base_model_name):
    model = AutoModelForCausalLM.from_pretrained(base_model_name, torch_dtype=torch.bfloat16, device_map="auto")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)

    tokenizer.padding_side = "left"
    tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer

from typing import Optional

def format_chat(
    tokenizer,
    prompt: str,
    response: Optional[str] = None,
    add_generation_prompt: bool = False,
    system_instruction: Optional[str] = None,
) -> str:

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("`prompt` must be a non-empty string.")

    if response is not None and not isinstance(response, str):
        raise TypeError("`response` must be a string or None.")

    if system_instruction is not None and not isinstance(system_instruction, str):
        raise TypeError("`system_instruction` must be a string or None.")

    messages = []

    if system_instruction is not None and system_instruction.strip():
        messages.append({"role": "system", "content": system_instruction.strip()})

    messages.append({"role": "user", "content": prompt.strip()})

    if response is not None:
        messages.append({"role": "assistant", "content": response.strip()})

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=add_generation_prompt,
    )

def make_incomplete_chat_response_prompt(tokenizer, user_request, response, system_instruction=None):
    temporal = "XXXXXX"
    temp = format_chat(tokenizer, user_request, temporal, system_instruction=system_instruction)
    before_response = temp[:temp.find(temporal)]
    output = before_response + response
    return output

def make_incomplete_chat_user_prompt(tokenizer, user_request, system_instruction=None):
    temporal = "XXXXXX"
    temp = format_chat(tokenizer, temporal, None, system_instruction=system_instruction)
    return temp[:temp.find(temporal)] + user_request




# user_request = "How can I make a chat incomplete?"
# incomplete_response = "Well,,"
# make_incomplete_chat_prompt(tokenizer, user_request, incomplete_response)
    
import torch
from tqdm import tqdm

def generate_response(model, tokenizer, prompts, batch_size=8, max_new_tokens=128):
    all_decoded_outputs = []

    # 1. Iterate through the prompts in chunks (batches)
    for i in tqdm(range(0, len(prompts), batch_size), desc="Generating responses"):
        batch_prompts = prompts[i : i + batch_size]
        
        # 2. Tokenize the current batch
        inputs = tokenizer(
            batch_prompts, 
            return_tensors="pt", 
            padding=True, 
            truncation=True
        ).to(model.device)
        
        # 3. Generate outputs with gradient calculation disabled for efficiency
        with torch.no_grad():
            outputs = model.generate(
                **inputs,  # Unpacks input_ids and attention_mask automatically
                max_new_tokens=max_new_tokens, 
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id
            )
        
        # 4. Decode only the new tokens (removing the prompt)
        batch_outputs = [
            tokenizer.decode(output[int(inputs.attention_mask[row_idx].sum().item()):], skip_special_tokens=True)
            for row_idx, output in enumerate(outputs)
        ]
        
        all_decoded_outputs.extend(batch_outputs)

    return all_decoded_outputs
