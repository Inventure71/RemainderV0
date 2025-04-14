from DatabaseUtils.database_projects import ProjectsDatabaseHandler

instance3 = ProjectsDatabaseHandler()
print(instance3.get_projects())
instance1 = ProjectsDatabaseHandler()
instance1.get_all_projects()
print(instance1.get_projects())
instance2 = ProjectsDatabaseHandler()
print(instance2.get_projects())

