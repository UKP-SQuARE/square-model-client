import ast
import os
import base64
import json
import logging
import time
from io import BytesIO
from typing import Dict, Iterable

import numpy as np
import requests
import urllib3

from square_model_client import client_credentials

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


class SQuAREModelClient:
    """
    This client provides an easy interface to the model-api
    from the square project.
    It handles authentication, sends the requests and for
    those that only return the task id it
    waits until the results are computed
    """

    def __init__(self):
        """
        This method initializes the client and the credentials which
        will be needed for each access.
        Args:
            api_url (str): The base url of the model-api
            client_secret (str): The secret of the client needed for authentication
            verify_ssl (bool): Whether the ssl should be verified
            keycloak_base_url (str): the base url of the keycloak server
            realm (str): the realm used by the client credentials
            client_id (str): the client id used by the client credentials
        """
        self.square_api_url = os.getenv("SQUARE_API_URL")
        self.verify_ssl = os.getenv("VERIFY_SSL") == "1"
        self.max_attempts = 50
        self.poll_interval = 2

    def decode_model_api_response(self, model_api_response: Dict) -> Dict:
        """Decode (if necessary) the model output of the Model API response and make
        it intonumpy arrays.

        Args:
            model_api_response (Dict): The response from the API

        Raises:
            ValueError: Raises ValueError when unexpected types (not `str` or
            `Iterbale`) are provided.

        Returns:
            Dict: model_api_response with 'model_outputs' decoded and parsed to numpy
        """

        # Decode byte base64 string back to numpy array
        def _decode(arr_string_b64):
            arr_binary_b64 = arr_string_b64.encode()
            arr_binary = base64.decodebytes(arr_binary_b64)
            arr = np.load(BytesIO(arr_binary))
            return arr

        # Recursively go through a value and decodeleaves (=str) or iterate over values and decode them
        def dec_or_iterate(val):
            if isinstance(val, str):
                return _decode(val)
            elif isinstance(val, Iterable):
                return [dec_or_iterate(v) for v in val]
            else:
                raise ValueError(
                    f"Encountered unexpected value {type(val)} while trying to decode "
                    f"the model output of the model API. Expected str or iterable."
                )

        if model_api_response["model_output_is_encoded"]:
            model_api_response["model_outputs"] = {
                key: dec_or_iterate(arr)
                for key, arr in model_api_response["model_outputs"].items()
            }
        else:
            model_api_response["model_outputs"] = {
                key: np.array(arr)
                for key, arr in model_api_response["model_outputs"].items()
            }
        return model_api_response

    def _wait_for_task(
        self,
        task_id: str,
        max_attempts=None,
        poll_interval=None,
    ):
        """
        Handling waiting for a task to finish. While the task has
        not finished request the result from the task_result
        endpoint and check whether it is finished
        Args:
             task_id (str): the id of the task
             max_attempts (int, optional): the maximum number of
                attempts to get the result. If this is None the
                self.max_attempts is used. The default is None.
             poll_interval (int, optional): the interval between the
                attempts to poll the results. If this is None
                self.poll_intervall is used. Defaults to None.
        """
        if max_attempts is None:
            max_attempts = self.max_attempts
        if poll_interval is None:
            poll_interval = self.poll_interval
        attempts = 0
        result = None

        while attempts < max_attempts:
            attempts += 1
            response = requests.get(
                url=f"{self.square_api_url}/main/task_result/{task_id}",
                headers={"Authorization": f"Bearer {client_credentials()}"},
                verify=self.verify_ssl,
            )
            resp = response.json()

            if response.status_code == 200:
                result = resp
                break
            time.sleep(poll_interval)
        return result["result"]

    def __call__(self, model_name: str, pipeline: str, model_request: Dict) -> Dict:
        prediction = self.predict(
            model_identifier=model_name,
            prediction_method=pipeline,
            input_data=model_request,
        )
        prediction = self.decode_model_api_response(prediction)

        return prediction

    def predict(self, model_identifier, prediction_method, input_data):
        """
        Request model prediction.
        Args:
            model_identifier (str): the identifier of the model that
                should be used for the prediction
            prediction_method (str): what kind of prediction should
                be made. Possible values are embedding,
                sequence-classification, token-classification,
                generation, question-answering
            input_data (Dict): the input for the prediction
        """
        supported_prediction_methods = [
            "embedding",
            "sequence-classification",
            "token-classification",
            "generation",
            "question-answering",
        ]
        if prediction_method not in supported_prediction_methods:
            raise ValueError(
                f"Unknown prediction_method {prediction_method}. "
                f"Please choose one of the following "
                f"{supported_prediction_methods}"
            )

        url = f"{self.square_api_url}/main/{model_identifier}/{prediction_method}"
        logger.debug(f"Requesting prediction from {url} with input {input_data}")
        response = requests.post(
            url=url,
            json=input_data,
            headers={
                "Authorization": f"Bearer {client_credentials()}",
                "Content-Type": "application/json",
            },
            verify=self.verify_ssl,
        )
        result = response.json()

        if response.status_code == 200:
            return self._wait_for_task(result["task_id"])
        else:
            return response

    def stats(self, model_identifier):
        """
        Get the statistics from the model with the given identifier
        Args:
            model_identifier(str): the identifier of the model
                to provide the statistics for
        """
        response = requests.get(
            url=f"{self.square_api_url}/main/{model_identifier}/stats",
            headers={"Authorization": f"Bearer {client_credentials()}"},
            verify=self.verify_ssl,
        )
        return response.json()

    def deployed_models(self):
        """
        Get all deployed models and their statistics
        """
        response = requests.get(
            url=f"{self.square_api_url}/models/deployed-models",
            headers={"Authorization": f"Bearer {client_credentials()}"},
            verify=self.verify_ssl,
        )
        return response.json()

    def deployed_model_workers(self):
        """
        Get all deployed models and their statistics
        """
        response = requests.get(
            url=f"{self.square_api_url}/models/deployed-model-workers",
            headers={"Authorization": f"Bearer {client_credentials()}"},
            verify=self.verify_ssl,
        )
        return response.json()

    def deploy(self, model_attributes):
        """
        Deploy a new model.
        Args:
            model_attributes (Dict): the attributes of the deployed models.
                An example would be:
                {
                    "identifier": "bert",
                    "model_name": "bert-base-uncased",
                    "model_type": "transformer",
                    "disable_gpu": True,
                    "batch_size": 32,
                    "max_input": 1024,
                    "transformers_cache": "../.cache",
                    "model_class": "base",
                    "return_plaintext_arrays": False,
                    "preloaded_adapters": True
                }
        """

        response = requests.post(
            url=f"{self.square_api_url}/models/deploy",
            json=model_attributes,
            headers={"Authorization": f"Bearer {client_credentials()}"},
            verify=self.verify_ssl,
        )
        result = response.json()

        if response.status_code == 200:
            return self._wait_for_task(result["task_id"], poll_interval=20)
        else:
            return response

    def remove(self, model_identifier):
        """
        Remove the model with the given identifier
        Args:
            model_identifier (str): the identifier of the model that should be removed
        """

        response = requests.delete(
            url=f"{self.square_api_url}/models/remove/{model_identifier}",
            json=model_identifier,
            headers={"Authorization": f"Bearer {client_credentials()}"},
            verify=self.verify_ssl,
        )
        result = response.json()

        if response.status_code == 200:
            return self._wait_for_task(result["task_id"])
        else:
            return response

    def update(self, model_identifier, updated_attributes):
        """
        Updating the attributes of a deployed model. Note that
        only disable_gpu, batch_size,
        max_input, return_plaintext_arrays can be changed.
        Args:
            model_identifier (str): the identifier of the model
                that should be updated
            updated_attributes (Dict): the new attributes of the model.
                An example could look like this:
                {
                    "disable_gpu": True,
                    "batch_size": 32,
                    "max_input": 256,
                    "return_plaintext_arrays": True
                }
        """
        response = requests.patch(
            url=f"{self.square_api_url}/models/update/{model_identifier}",
            headers={"Authorization": f"Bearer {client_credentials()}"},
            json=updated_attributes,
            verify=self.verify_ssl,
        )
        return response.json()

    def add_worker(self, model_identifier, number):
        """
        Adds workers of a specific model such that heavy
        workloads can be handled better.
        Note, that only the creater of the model is allowed to add
        new workers and only admins are allowed to have more than 2
        workers for each model.
        Args:
            model_identifier (str): the identifier of the model
                to add workers for
            number (int): the number of workers to add
        """

        response = requests.patch(
            url=f"{self.square_api_url}/models/{model_identifier}/add_worker/{number}",
            json=model_identifier,
            headers={"Authorization": f"Bearer {client_credentials()}"},
            verify=self.verify_ssl,
        )
        result = response.json()
        if response.status_code == 200:
            return self._wait_for_task(result["task_id"])
        else:
            return response

    def remove_worker(self, model_identifier, number):
        """
        Remove/down-scale model worker
        """

        response = requests.patch(
            url=f"{self.square_api_url}/models/{model_identifier}/remove_worker/{number}",
            json=model_identifier,
            headers={"Authorization": f"Bearer {client_credentials()}"},
            verify=self.verify_ssl,
        )
        result = response.json()
        if response.status_code == 200:
            return self._wait_for_task(result["task_id"])
        else:
            return response

    def get_models_in_deployment(self) -> Dict[str, str]:
        """Returns dict mapping of model names to types are currently beeing deployed."""
        token = client_credentials()
        response = requests.get(
            f"{self.square_api_url}/models/task",
            headers=dict(Authorization=f"Bearer {token}"),
        )
        logger.debug(f"get running tasks {response.text}")

        response.raise_for_status()

        running_tasks = response.json()
        models_in_deployment = {}
        for worker2tasks in running_tasks.values():
            for tasks in worker2tasks.values():
                for task in tasks:
                    if task["name"] == "tasks.tasks.deploy_task":
                        model_name = task["args"][0]["MODEL_NAME"]
                        model_type = task["args"][0]["MODEL_TYPE"]
                        models_in_deployment[model_name] = model_type

        return models_in_deployment

    def deploy_model_if_not_exists(self, default_skill_args: Dict):
        """Deploys a model if it is not deployed and not currently deploying."""
        model_name = default_skill_args.get("base_model")
        if not model_name:
            logger.info("No base_model in the skill args. Nothing to deploy.")
            return
        model_type = "adapter" if "adapter" in default_skill_args else "transformer"
        logger.info(
            f"Checking if model={model_name} with model_type={model_type} is already deployed."
        )

        deployed_models = self.deployed_models()

        if any(model['model_name'] == model_name and model['model_type'] == model_type for model in deployed_models):
            logger.info(
                f"model={model_name} with model_type={model_type} is already deployed."
            )
            return

        currently_deploying_models = self.get_models_in_deployment()
        if currently_deploying_models.get(model_name, "") == model_type:
            logger.info(
                f"model={model_name} with model_type={model_type} is in deployment."
            )
            return

        logger.info(
            f"model={model_name} with model_type={model_type} is not deployed. Starting deployment."
        )
        self.deploy(model_attributes={
            "identifier": model_name,
            "model_name": model_name,
            "model_type": model_type,
        })
