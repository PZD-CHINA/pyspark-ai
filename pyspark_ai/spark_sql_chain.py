from typing import Any, List, Optional

from langchain.callbacks.base import Callbacks
from langchain.chains import LLMChain
from langchain.chat_models.base import BaseChatModel
from langchain.schema import BaseMessage, HumanMessage
from pyspark.sql import SparkSession
from langchain_core.language_models.llms import BaseLLM

from pyspark_ai.ai_utils import AIUtils
from pyspark_ai.code_logger import CodeLogger


class SparkSQLChain(LLMChain):
    """
    LLM Chain for generating SQL code for DataFrame transform.
    It supports retrying if the generated query fails the SQL compiler.
    """

    spark: SparkSession
    logger: CodeLogger = None
    max_retries: int = 3

    def run(
        self,
        *args: Any,
        callbacks: Callbacks = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        assert not args, "The chain expected no arguments"
        # assert llm is an instance of BaseChatModel
        #assert isinstance(
        #    self.llm, BaseChatModel
        #), "The llm is not an instance of BaseChatModel"
        prompt_str = self.prompt.format_prompt(**kwargs).to_string()
        print(f"-------------------------Input prompt is:-------------------------\n\n {prompt_str}\n")
        messages = [HumanMessage(content=prompt_str)]
        return self._generate_code_with_retries(self.llm, messages, self.max_retries)

    def _generate_code_with_retries(
        self,
        chat_model: BaseLLM,
        messages: List[BaseMessage],
        retries: int = 3,
    ) -> str:
        response = chat_model.predict_messages(messages)
        print(f"-------------------------The model replies:-------------------------\n\n {response.content} \n")
        #if self.logger is not None:
         #   self.logger.info(response.content)
        code = AIUtils.extract_code_blocks(response.content)[0]
        #code = response.content.split("\n")[1].split("Human:")[1].replace("`","")
        try:
            print(f"-------------------------Spark retrieved sql:-------------------------\n\n {code}\n")
            self.spark.sql(code)
            return code
        except Exception as e:
            if self.logger is not None:
                self.logger.warning("Getting the following error: \n" + str(e))
            if retries <= 0:
                # if we have no more retries, raise the exception
                self.logger.info(
                    "No more retries left, please modify the instruction or modify the generated code"
                )
                return ""
            if self.logger is not None:
                self.logger.info("Retrying with " + str(retries) + " retries left")

            # messages.append(response)
            # Remove retry logic to prevent long response append and ensure accurate model results.
            
            # append the exception as a HumanMessage into messages
            # messages.append(HumanMessage(content=str(e)))
            # Remove retry logic to prevent long response append and ensure accurate model results.
            return self._generate_code_with_retries(chat_model, messages, retries - 1)
