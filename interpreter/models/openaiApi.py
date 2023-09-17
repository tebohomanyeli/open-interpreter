#------------------------------------------------------------------------------Imports
import os
import time
import json
import platform
import openai
import getpass
import requests
import readline
import urllib.parse
import tokentrim as tt
from rich import print
from rich.markdown import Markdown
from rich.rule import Rule

#------------------------------------------------------------------------------Local Files
from .cli import cli
from .utils import merge_deltas, parse_partial_json
from .message_block import MessageBlock
from .code_block import CodeBlock
from .code_interpreter import CodeInterpreter
from .llama_2 import get_llama_2_instance

#------------------------------------------------------------------------------Subdirectory
from .interpreter_components.cli_messages import missing_api_key_message
from .interpreter_components.cli_messages import missing_azure_info_message
from .interpreter_components.cli_messages import confirm_mode_message
from .interpreter_components.model_schema import function_schema

class Interpreter:

    def __init__(self):
        #TODO THIS METHOD IS SIMPLY INITIALISING A MODE
        pass


    def cli(self):
        # The cli takes the current instance of Interpreter,
        # modifies it according to command line flags, then runs chat.
        cli(self)


    def get_info_for_system_message(self):
        """
        Gets relevent information for the system message.
        """

        info = ""
        return info


    def reset(self):
        self.messages = []
        self.code_interpreters = {}


    def load(self, messages):
        self.messages = messages


    def chat(self, message=None, return_messages=False):

        # Connect to an LLM (an large language model)
        pass


    def verify_api_key(self):
        """
        Makes sure we have an AZURE_API_KEY or OPENAI_API_KEY.
        """
        pass


    def end_active_block(self):
        if self.active_block:
            self.active_block.end()
            self.active_block = None


    def respond(self):
        # Add relevant info to system_message
        pass