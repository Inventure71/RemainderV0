from DatabaseUtils.database_projects import ProjectsDatabaseHandler
from DatabaseUtils.database_messages import MessageDatabaseHandler

instance1 = MessageDatabaseHandler()
print(instance1.get_project_messages("muuuu"))




