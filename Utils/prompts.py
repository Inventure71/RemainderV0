

# 0
sys_prompt_answer_question = """
You are given a list of messages, your goal is to answer the query from the user in the most relevant way using them as source. Do not list all the messages unless requested to do so. Give short and concise answers. At the end of the message cite the used messages by writing a python list with their IDs, es: [1,14,33].
"""

# 1
sys_prompt_select_messages = """You are given a list of messages, list the messages that might correspond to the user query, for each message specify:
1) id, the id of the message
2) content, the content of the message (only the first 30 words)
3) why, justify why the message is included
"""

# 2
sys_prompt_select_projects = """
Your given context: a list of projects, their description and the first 5 messages of each project.
Your input: a list of messages from the main chat.

Your task: process the messages of the main chat, assign them to the appropriate projects, if the message does not correspond to any project precisely, assign it to the empty project "" or leave them out of your response.
Note: when evaluating a message consider also the preceding and subsequent messages, some messages might be related and the user might have specified stuff only once.

For each message that you assign, specify:
1) id, the id of the message
2) project, the name of the project
3) why, justify why the message is assigned to this project (max 10 words)

For each message also you have an optional feature that is independent from the previous task, you need to identify if the message should be reminded to the user:
Messages to include:
- any messages that say explicitly that they should be reminded
- any message that the user wants to be reminded about, even indirectly, these can be of many kinds but can be identified because they are either really concise actions or requests, es: "Buy milk" or "Call mom" or "Find Verstappen's latest news"
    - some messages such as "Search for max Verstappen clothes" might not contain express indications to be reminded, in these cases set the remind date to 23:00 of the current day. 

If a message does not state the time when it should be reminded, set the remind date to 23:00 of the current day.

The extra parameters that will need to be filled in this task are:
1) id, the id of the message
2) when, when does the message need to be reminded, use year-month-day-hour-minute format, es: 2005-10-31-14:25 another example 2025-01-02-23:00
3) importance, from a scale from 1 to 10 how important it is to remember, where 1 is almost irrelevant and 10 is extremely time sensitive, if the user specify a time or day give a number equal or higher than 8, if indecisive give a 7
If the message doesn't need to be reminded then omit the extra fields or give an importance 0

If the message is both in task one and task 2 only specify ID once.
Note that this second task is independent from the task of identifying the projects, a message might need to be reminded and not needing to be inserted in any project, the opposite, both or neither. 
"""

# 3
sys_prompt_create_projects = """
Your given context: a list of projects, their description and the first 5 messages of each project.
Your input: A list of messages that are not part of a project yet.

Your task: Understand if any messages could be organized in projects (collections) that don't exist yet, for each new project that should be created specify:
1) Name, the name of the project
2) Description, a short description of the project (max 200 words)

Note: when evaluating a message consider also the preceding and subsequent messages, some messages might be related and the user might have specified stuff only once.
Each project is a collection of messages that are related to each other in someway.
Return a list of projects, es: [projects: [{"name": "Project Name", "description": "Project Description"}]]
"""

# 4
