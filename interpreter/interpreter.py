# ------------------------------------------------------------------------------Imports
import os
import time
# import json
import platform
# import openai
import getpass
# import requests
import readline
# import urllib.parse
import tokentrim as tt
from rich import print
from rich.markdown import Markdown
from rich.rule import Rule

# ------------------------------------------------------------------------------Local Files
from .cli import cli
from .utils import merge_deltas #, parse_partial_json
from .message_block import MessageBlock
from .code_block import CodeBlock
from .code_interpreter import CodeInterpreter
from .llama_2 import get_llama_2_instance
from .hugchat import HugChat

# ------------------------------------------------------------------------------Subdirectory
from .interpreter_components.cli_messages import confirm_mode_message


class Interpreter:

    def __init__(self):
        # TODO THIS METHOD IS SIMPLY INITIALISING A MODE
        # SO WE CAN FIND A BETTER WAY TO DO THIS THAT ALLOWS FOR EASY PLUGIN
        self.messages = []
        self.temperature = 0.001
        self.api_key = None
        self.auto_run = False
        self.local = False
        self.model = "gpt-4"
        self.debug_mode = False

        # Get default system message
        here = os.path.abspath(os.path.dirname(__file__))
        with open(os.path.join(here, 'system_message.txt'), 'r') as f:
            self.system_message = f.read().strip()

        # Store Code Interpreter instances for each language
        self.code_interpreters = {}

        # No active block to start
        # (blocks are visual representation of messages on the terminal)
        self.active_block = None

        # Note: While Open Interpreter can use Llama, we will prioritize gpt-4.
        # gpt-4 is faster, smarter, can call functions, and is all-around easier to use.
        # This makes gpt-4 better aligned with Open Interpreters priority to be easy to use.
        self.llama_instance = None

    def cli(self):
        # The cli takes the current instance of Interpreter,
        # modifies it according to command line flags, then runs chat.
        cli(self)

    def get_info_for_system_message(self):
        """
        Gets relevant information for the system message.
        """

        info = ""

        # Add user info
        username = getpass.getuser()
        current_working_directory = os.getcwd()
        operating_system = platform.system()

        info += f"[User Info]\nName: {username}\nCWD: {current_working_directory}\nOS: {operating_system}"

        # Tell Code-Llama how to run code.
        info += ("\n\nTo run code, write a fenced code block (i.e ```python or ```shell) in markdown. When you close "
                 "it with ```, it will be run. You'll then be given its output.")
        # We make references in system_message.txt to the "function" it can call, "run_code".

        return info

    def reset(self):
        self.messages = []
        self.code_interpreters = {}

    def load(self, messages):
        self.messages = messages

    def chat(self, message=None, return_messages=False):

        # Connect to an LLM (a large language model)
        self.verify_api_key()

        # ^ verify_api_key may set self.local to True, so we run this as an 'if', not 'elif':
        if self.local:
            self.model = "code-llama"

            # Code-Llama
            if self.llama_instance is None:

                # Find or install Code-Llama
                try:
                    self.llama_instance = HugChat.get_hugchat_instance()
                except:
                    # If it didn't work, apologize and switch to GPT-4

                    print(Markdown("".join([
                        "> Failed to install `Code-LLama`.",
                        "\n\n**We have likely not built the proper `Code-Llama` support for your system.**",
                        "\n\n*( Running language models locally is a difficult task!* If you have insight into the best way to implement this across platforms/architectures, please join the Open Interpreter community Discord and consider contributing the project's development. )",
                        "\n\nPlease press enter to switch to `GPT-4` (recommended)."
                    ])))
                    input()

        # Display welcome message
        welcome_message = ""

        if self.debug_mode:
            welcome_message += "> Entered debug mode"

        # If self.local, we actually don't use self.model
        # (self.auto_run is like advanced usage, we display no messages)
        if not self.local and not self.auto_run:
            welcome_message += f"\n> Model set to `{self.model.upper()}`\n\n**Tip:** To run locally, use `interpreter --local`"

        if self.local:
            welcome_message += f"\n> Model set to `Code-Llama`"

        # If not auto_run, tell the user we'll ask permission to run code
        # We also tell them here how to exit Open Interpreter
        if not self.auto_run:
            welcome_message += "\n\n" + confirm_mode_message

        welcome_message = welcome_message.strip()

        # Print welcome message with newlines on either side (aesthetic choice)
        # unless we're starting with a blockquote (aesthetic choice)
        if welcome_message != "":
            if welcome_message.startswith(">"):
                print(Markdown(welcome_message), '')
            else:
                print('', Markdown(welcome_message), '')

        # Check if `message` was passed in by user
        if message:
            # If it was, we respond non-interactivley
            self.messages.append({"role": "user", "content": message})
            self.respond()

        else:
            # If it wasn't, we start an interactive chat
            while True:
                try:
                    user_input = input("> ").strip()
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print()  # Aesthetic choice
                    break

                # Use `readline` to let users up-arrow to previous user messages,
                # which is a common behavior in terminals.
                readline.add_history(user_input)

                # Add the user message to self.messages
                self.messages.append({"role": "user", "content": user_input})

                # Let the user turn on debug mode mid-chat
                if user_input == "%debug":
                    print('', Markdown("> Entered debug mode"), '')
                    print(self.messages)
                    self.debug_mode = True
                    continue

                # Respond, but gracefully handle CTRL-C / KeyboardInterrupt
                try:
                    self.respond()
                except KeyboardInterrupt:
                    pass
                finally:
                    # Always end the active block. Multiple Live displays = issues
                    self.end_active_block()

        if return_messages:
            return self.messages

    def verify_api_key(self):
        """
        Configures the system to use the local model.
        """
        self.local = True
        print(Markdown("> Switching to `Code-Llama`..."))
        time.sleep(2)
        print(Rule(style="white"))

    def end_active_block(self):
        if self.active_block:
            self.active_block.end()
            self.active_block = None

    def respond(self):
        # Add relevant info to system_message
        # (e.g. current working directory, username, os, etc.)
        info = self.get_info_for_system_message()

        # This is hacky, as we should have a different (minified) prompt for CodeLLama,
        # but for now, to make the prompt shorter and remove "run_code" references, just get the first 2 lines:
        if self.local:
            self.system_message = "\n".join(self.system_message.split("\n")[:3])
            self.system_message += "\nOnly do what the user asks you to do, then ask what they'd like to do next."

        system_message = self.system_message + "\n\n" + info

        if self.local:
            messages = tt.trim(self.messages, max_tokens=1048, system_message=system_message)
        else:
            messages = tt.trim(self.messages, self.model, system_message=system_message)

        if self.debug_mode:
            print("\n", "Sending `messages` to LLM:", "\n")
            print(messages)
            print()

        # Make LLM call

        if self.local:
            # Code-Llama

            # Convert messages to prompt
            # (This only works if the first message is the only system message)

            def messages_to_prompt(messages):
                # Extracting the system prompt and initializing the formatted string with it.
                system_prompt = messages[0]['content']
                formatted_messages = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n"

                for message in messages:
                    # Happens if it immediatly writes code
                    if "role" not in message:
                        message["role"] = "assistant"

                # Loop starting from the first user message
                for index, item in enumerate(messages[1:]):
                    role = item['role']
                    content = item['content']

                    if role == 'user':
                        formatted_messages += f"{content} [/INST] "
                    elif role == 'function':
                        formatted_messages += f"Output: {content} [/INST] "
                    elif role == 'assistant':
                        formatted_messages += f"{content} </s><s>[INST] "

                # Remove the trailing '<s>[INST] ' from the final output
                if formatted_messages.endswith("<s>[INST] "):
                    formatted_messages = formatted_messages[:-10]

                return formatted_messages

            prompt = messages_to_prompt(messages)
            # Lmao i can't believe this works (it does need this btw)
            if messages[-1]["role"] != "function":
                prompt += ("Let's explore this. By the way, I can run code on your machine by writing the code in a "
                           "markdown code block. This works for shell, javascript, python, and applescript. I'm going "
                           "to try to do this for your task. Anyway,")
            elif messages[-1]["role"] == "function" and messages[-1]["content"] != "No output":
                prompt += "Given the output of the code I just ran, "
            elif messages[-1]["role"] == "function" and messages[-1]["content"] == "No output":
                prompt += "Given the fact that the code I just ran produced no output, "

            if self.debug_mode:
                # we have to use builtins bizarrely! because rich.print interprets "[INST]" as something meaningful
                import builtins
                builtins.print("TEXT PROMPT SEND TO LLM:\n", prompt)

            # Run Code-Llama

            response = self.llama_instance(prompt)
            # print(str(type(response)) + " " + str(response))


        # Initialize message, function call trackers, and active block
        self.messages.append({})
        in_function_call = False
        llama_function_call_finished = False
        self.active_block = None

        for chunk in response:

            if self.local:
                if "content" not in messages[-1]:
                    # This is the first chunk. We'll need to capitalize it, because our prompt ends in a ", "
                    chunk["choices"][0]["text"] = chunk["choices"][0]["text"].capitalize()
                    # We'll also need to add "role: assistant", CodeLlama will not generate this
                    messages[-1]["role"] = "assistant"
                delta = {"content": chunk["choices"][0]["text"]}
            else:
                delta = chunk["choices"][0]["delta"]

            # Accumulate deltas into the last message in messages
            self.messages[-1] = merge_deltas(self.messages[-1], delta)

            condition = False
            if self.local:
                # Since Code-Llama can't call functions, we just check if we're in a code block.
                # This simply returns true if the number of "```" in the message is odd.
                if "content" in self.messages[-1]:
                    condition = self.messages[-1]["content"].count("```") % 2 == 1
                else:
                    # If it hasn't made "content" yet, we're certainly not in a function call.
                    condition = False

            if condition:
                # We are in a function call.

                # Check if we just entered a function call
                if not in_function_call:

                    # If so, end the last block,
                    self.end_active_block()

                    # Print newline if it was just a code block or user message
                    # (this just looks nice)
                    last_role = self.messages[-2]["role"]
                    if last_role == "user" or last_role == "function":
                        print()

                    # then create a new code block
                    self.active_block = CodeBlock()

                # Remember we're in a function_call
                in_function_call = True

                # Now let's parse the function's arguments:

                if self.local:
                    # Code-Llama
                    # Parse current code block and save to parsed_arguments, under function_call
                    if "content" in self.messages[-1]:

                        content = self.messages[-1]["content"]

                        if "```" in content:
                            # Split by "```" to get the last open code block
                            blocks = content.split("```")

                            current_code_block = blocks[-1]

                            lines = current_code_block.split("\n")

                            if content.strip() == "```":  # Hasn't outputted a language yet
                                language = None
                            else:
                                language = lines[0].strip() if lines[0] != "" else "python"

                            # Join all lines except for the language line
                            code = '\n'.join(lines[1:]).strip("` \n")

                            arguments = {"code": code}
                            if language:  # We only add this if we have it-- the second we have it, an interpreter gets fired up (I think? maybe I'm wrong)
                                arguments["language"] = language

                        # Code-Llama won't make a "function_call" property for us to store this under, so:
                        if "function_call" not in self.messages[-1]:
                            self.messages[-1]["function_call"] = {}

                        self.messages[-1]["function_call"]["parsed_arguments"] = arguments

            else:
                # We are not in a function call.

                # Check if we just left a function call
                if in_function_call:

                    if self.local:
                        # This is the same as when gpt-4 gives finish_reason as function_call.
                        # We have just finished a code block, so now we should run it.
                        llama_function_call_finished = True

                # Remember we're not in a function_call
                in_function_call = False

                # If there's no active block,
                if self.active_block is None:
                    # Create a message block
                    self.active_block = MessageBlock()

            # Update active_block
            self.active_block.update_from_message(self.messages[-1])

            # Check if we're finished
            if chunk["choices"][0]["finish_reason"] or llama_function_call_finished:
                if chunk["choices"][
                    0]["finish_reason"] == "function_call" or llama_function_call_finished:
                    # Time to call the function!
                    # (Because this is Open Interpreter, we only have one function.)

                    if self.debug_mode:
                        print("Running function:")
                        print(self.messages[-1])
                        print("---")

                    # Ask for user confirmation to run code
                    if not self.auto_run:

                        # End the active block so you can run input() below it
                        # Save language and code so we can create a new block in a moment
                        self.active_block.end()
                        language = self.active_block.language
                        code = self.active_block.code

                        # Prompt user
                        response = input("  Would you like to run this code? (y/n)\n\n  ")
                        print("")  # <- Aesthetic choice

                        if response.strip().lower() == "y":
                            # Create a new, identical block where the code will actually be run
                            self.active_block = CodeBlock()
                            self.active_block.language = language
                            self.active_block.code = code

                        else:
                            # User declined to run code.
                            self.active_block.end()
                            self.messages.append({
                                "role":
                                    "function",
                                "name":
                                    "run_code",
                                "content":
                                    "User decided not to run this code."
                            })
                            return

                    # Create or retrieve a Code Interpreter for this language
                    language = self.messages[-1]["function_call"]["parsed_arguments"][
                        "language"]
                    if language not in self.code_interpreters:
                        self.code_interpreters[language] = CodeInterpreter(language, self.debug_mode)
                    code_interpreter = self.code_interpreters[language]

                    # Let this Code Interpreter control the active_block
                    code_interpreter.active_block = self.active_block
                    code_interpreter.run()

                    # End the active_block
                    self.active_block.end()

                    # Append the output to messages
                    # Explicitly tell it if there was no output (sometimes "" = hallucinates output)
                    self.messages.append({
                        "role": "function",
                        "name": "run_code",
                        "content": self.active_block.output if self.active_block.output else "No output"
                    })

                    # Go around again
                    self.respond()

                if chunk["choices"][0]["finish_reason"] != "function_call":
                    # Done!

                    # Code Llama likes to output "###" at the end of every message for some reason
                    if self.local and "content" in self.messages[-1]:
                        self.messages[-1]["content"] = self.messages[-1]["content"].strip().rstrip("#")
                        self.active_block.update_from_message(self.messages[-1])
                        time.sleep(0.1)

                    self.active_block.end()
                    return
