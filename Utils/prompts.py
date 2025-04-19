


sys_prompt_0 = """
You are given a list of messages, your goal is to answer the query from the user in the most relevant way using them as source. Do not list all the messages unless requested to do so. Give short and concise answers. At the end of the message cite the used messages by writing a python list with their IDs, es: [1,14,33].
"""

sys_prompt_1 = """You are given a list of messages, list the messages that might correspond to the user query, for each message specify:
1) id, the id of the message
2) content, the content of the message (only the first 30 words)
3) why, justify why the message is included
"""

sys_prompt_2 = ""

