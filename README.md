# Commit Jira Audit tool

This script analyzes commits in the release branch and searches for mentions of Jira tasks in the commit messages. It then searches Jira for the corresponding release and creates a report based on the related tasks. The report includes information such as:
- Are there any tasks that have no corresponding commits?
- Are there commits that do not correspond to any task in the current release?
- Are any tasks still open in this release?
- Is there a specific instruction for the release?
- Who is responsible for deploying the release?

Script Logic:
1. We get the difference between the release branch and the master branch.
2. We look for mentions of Jira tasks in the commit headers.
3. We obtain a list of versions from Jira and search for a version by the number indicated in the name of the release branch.
4. We receive a list of related tasks, save separately the unclosed tasks and tasks that are instructions for the release.
5. We compare tasks received from commits with the Jira version and save the differences as a result. You can also exclude MRs and RFCs.
6. The data received can be transferred to a template engine for visualization.