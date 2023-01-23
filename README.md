# SQuARE Model Client
This package facilites the interaction with models hosted in [UKP-SQuARE](https://square.ukp-lab.de/).

## Installation
```bash
pip install square-model-client
```

## Usage
After installing, models in SQuARE can be called easily. Before running the code, the following environment variables need to be set.
```bash
export SQUARE_API_URL=https://square.ukp-lab.de/api
export KEYCLOAK_BASE_URL=https://square.ukp-lab.de
export REALM=square
export CLIENT_ID=<INSERT>
export CLIENT_SECRET=<INSERT>
```
- `SQUARE_API_URL`: The address where the SQuARE API's are hosted. For UKP-SQuARE set this to `https://square.ukp-lab.de/api`. If you run SQuARE locally, set this to your address.
- `KEYCLOAK_BASE_URL`: The address where tokens can be obtained from. For UKP-SQuARE set this to `https://square.ukp-lab.de`
- `REALM`: The realm in which your Keycloak client resides. For UKP-SQuARE this is `square`.
- `CLIENT_ID`: The ID of your client. For UKP-SQuARE, you will receive this from the UI when creating a new skill.*
- `CLIENT_SECRET`: The secret of your client/skill. For UKP-SQuARE, you will receive this from the UI when creating a new skill.*

*) This is currently not supported in the UI. However, when you open the developer tab in your browser, you will see the response from the API containing the `CLIENT_ID` and `CLIENT_SECRET`.

```python
import asyncio

from square_model_client import SQuAREModelClient

async def main():
    square_model_client = SQuAREModelClient()

    query = "When was TU Darmstadt established?"
    context = ["The Technische Universität Darmstadt, commonly known as TU Darmstadt, is a research university in the city of Darmstadt, Germany. It was founded in 1877 and received the right to award doctorates in 1899."]
   
    model_request = {
        "input": [[query, c] for c in context],
        "task_kwargs": {"topk": 2},
        "adapter_name": "qa/squad2@ukp"
    }

    model_api_output = await square_model_client(
        model_name="bert-base-uncased", 
        pipeline="question-answering", 
        model_request=model_request
    )
    print(*model_api_output['answers'][0], sep="\n")
    # {'score': 0.9326951503753662, 'start': 148, 'end': 152, 'answer': '1877'}
    # {'score': 0.05753004178404808, 'start': 145, 'end': 152, 'answer': 'in 1877'} 

# Note, the SQuAREModelCLient is usually called within an endpoint that is async. 
# In that case, the following line is not needed.
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
```
