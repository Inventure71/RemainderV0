


sys_prompt_0 = """
You are given a list of messages, your goal is to answer the query from the user in the most relevant way using them as source. Do not list all the messages unless requested to do so. Give short and concise answers. At the end of the message cite the used messages by writing a python list with their IDs, es: [1,14,33].
"""

sys_prompt_1 = """You are given a list of messages, list the messages that might correspond to the user query, for each message specify:
1) id, the id of the message
2) content, the content of the message (only the first 30 words)
3) why, justify why the message is included
"""

sys_prompt_2 = """
Your given context: a list of projects, their description and the first 5 messages of each project.
Your input: a list of messages from the main chat.

Your task: process the messages of the main chat, assign them to the appropriate projects, if the message does not correspond to any project precisely, assign it to the empty project "" or leave them out of your response.

For each message that you assign, specify:
1) id, the id of the message
2) project, the name of the project
3) why, justify why the message is assigned to this project (max 10 words)
"""

sys_prompt_3 = """
Your given context: a list of projects, their description and the first 5 messages of each project.
Your input: a list of messages from the main chat.

Your task: Understand if any messages could be organized in collections that are yet not present, for each new collection specify:
1) Name, the name of the collection
2) Description, a short description of the collection (max 200 words)
"""
