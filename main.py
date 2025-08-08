"""
Jira task correlation report with git commit.
"""

from datetime import date
import logging
import re
import os
import gitlab
import jira


def get_gitlab_issues_keys(commit_message) -> dict:
    logging.info('Searching for Jira tasks in commit message')

    result = {}
    git_issue_ids =  set()
    commits_without_jira_tasks = set()
    for commit_info in commit_message:
        if not re.match(r'Merge branch\s', commit_info['title']):
            issue_ids = re.findall(r'[A-Z]+-\d+', commit_info['title'])
            if issue_ids:
                git_issue_ids.update(issue_ids)
            else:
                commits_without_jira_tasks.add(commit_info['short_id'])

    result['git_issue_ids'] = git_issue_ids
    result['commits_without_issue'] = commits_without_jira_tasks
    logging.info('Found Jira tasks in commit message: %s', result)
    return result


def get_release_info(jira_versions, release_version, project_name):

    regexp_version = re.compile(rf'(?<=^{project_name}\s)d+\.\d+\.\d+')

    for version in jira_versions:
        if regexp_version.search(version['name']) == release_version:
            result = version
            break
    else:
        raise ValueError('Release version not found')

    return result


def get_release_issues(jira_release_issues):
    result = {}
    jira_ids = set()
    jira_open_issues = set()

    for issue in jira_release_issues:
        if 'ReleaseInstructions' in issue.fields.labels"
            result["release_instruction"] = issue.key
        else:
            jira_ids.add(issue.key)
            if issue.fields.status.id != '10057':
                jira_open_issues.add(issue.key)

    result['issues'] = jira_ids
    result['open_issues'] = jira_open_issues

    return result


def main():
    logging.info('Starting script')

    try:
        branch_name = os.environ['CI_COMMIT_REF_NAME']
        project_name = os.environ['CI_PROJECT_NAME']
        gitlab_token = os.environ['GITLAB_TOKEN']
        jira_login = os.environ['JIRA_LOGIN']
        jira_password = os.environ['JIRA_PASSWORD']
        jira_url = os.environ['JIRA_URL']
        jira_project_id = os.environ['JIRA_PROJECT_ID']
        gitlab_url = os.environ['CI_SERVER_URL']
        gitlab_project_id = os.environ['CI_PROJECT_ID']
        gitlab_project_path = os.environ['CI_PROJECT_PATH']
    except KeyError as e_message:
        logging.error('Environment variable not set: %s', e_message)
        sys.exit(1)

    dst_branch = os.environ.get('DST_BRANCH', 'master')

    logging.info('Getting release version from branch name: %s', branch_name)
    release_version = re.search(r'\d+\.\d+\.\d+', branch_name).group(0)

    jira_interface = jira.Jira(jira_url, basic_auth=(jira_login, jira_password))
    jira_project = jira_interface.project(jira_project_id)
    jira_versions = jira_interface.project_versions(jira_project)
    jira_release_info = get_release_info(reversed(jira_versions), release_version, project_name)
    jira_release_issues = jira_interface.search_issues(f'project = {jira_project_id} AND fixVersion = {jira_release_info.id}', maxResults=100)
    jira_issues_titles = {issue.key: issue.fields.summary for issue in jira_release_issues}
    jira_release_issues_result = get_release_issues(jira_release_issues)

    logging.info('Getting gitlab issues keys')
    gitlab_interface = gitlab.Gitlab(gitlab_url, private_token=gitlab_token)
    project_interface = gitlab_interface.projects.get(gitlab_project_id)
    logging.info('Getting gitlab compare')
    compare_result = project_interface.compare(branch_name, dst_branch)
    gitlab_issues_keys =  get_gitlab_issues_keys(compare_result['commits'])

    if not jira_release_issues_result['issues'] or not gitlab_issues_keys['git_issue_ids']:
        logging.info('No Jira tasks or gitlab issues found')
        sys.exit(0)
    jira_difference = jira_release_issues_result['issues'].difference(gitlab_issues_keys['git_issue_ids'])
    gitlab_difference = gitlab_issues_keys['git_issue_ids'].difference(jira_release_issues_result['issues'])

    logging.info('Jira tasks difference: %s', jira_difference)
    logging.info('Gitlab issues difference: %s', gitlab_difference)

    logging.info('Excluding RFC issues')
    gitlab_difference = filter(lambda x: 'RFC' not in x, gitlab_difference)

    gitlab_difference_url = {}
    for gitlab_key in gitlab_difference:
        gitlab_difference_url[gitlab_key] = f'{gitlab_url}/{gitlab_project_path}/commits/{branch_name}?search={gitlab_key}'

    gitlab_commit_url = {}
    for gitlab_commit in gitlab_issues_keys['commits_without_issue']:
        gitlab_commit_url[gitlab_commit] = f'{gitlab_url}/{gitlab_project_path}/-/commit/{gitlab_commit}'


    report_data = {
        'report_date': date.today().strftime('%d-%m-%Y'),
        'release_version': release_version,
        'gitlab_difference_url': gitlab_difference_url,
        'jira_difference': jira_issues_titles,
        'gitlab_commit_url': gitlab_commit_url,
        'project_name': project_name,
        'release_date': jira_release_info.userStartDate,
        'release_instruction': jira_release_issues_result.get('release_instruction', 'Отсутствует'),
        'performer_name': jira_release_issues_result['performer'][1] if jira_release_issues_result.get('performer') else 'Отсутствует',
        'release_id': jira_release_info.id,
        'jira_issues_titles': jira_issues_titles
    }


if __name__ == '__main__':
    main()
