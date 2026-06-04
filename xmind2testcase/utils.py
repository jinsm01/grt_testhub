#!/usr/bin/env python
# _*_ coding:utf-8 _*_
import json
import os
import re
import logging

# 延迟导入 - 避免模块缓存问题
def _get_xmindparser():
    """延迟导入 xmindparser"""
    try:
        from xmindparser import xmind_to_dict
        return xmind_to_dict
    except ImportError:
        raise ImportError("请安装xmindparser: pip install xmindparser")

def _get_xmind():
    """延迟导入 xmind"""
    try:
        import xmind
        return xmind
    except ImportError:
        return None

# 避免循环导入 - 先导入非循环依赖的模块
from .parser import xmind_to_testsuites

# 定义自定义异常类，替代不存在的exceptions模块
class FileTypeError(Exception):
    """自定义文件类型错误异常"""
    pass


def get_absolute_path(path):
    """
        Return the absolute path of a file

        If path contains a start point (eg Unix '/') then use the specified start point
        instead of the current working directory. The starting point of the file path is
        allowed to begin with a tilde "~", which will be replaced with the user's home directory.
    """
    fp, fn = os.path.split(path)
    if not fp:
        fp = os.getcwd()
    fp = os.path.abspath(os.path.expanduser(fp))
    return os.path.join(fp, fn)


def get_xmind_testsuites(xmind_file):
    """Load the XMind file and parse to `xmind2testcase.metadata.TestSuite` list"""
    xmind_file = get_absolute_path(xmind_file)
    
    # 延迟导入解析器
    xmind_to_dict = _get_xmindparser()
    xmind = _get_xmind()
    
    # Try to parse using xmindparser first (for XMind Zen format)
    if xmind_to_dict:
        try:
            logging.info("Trying to parse with xmindparser (for XMind Zen format)")
            xmind_content_dict = xmind_to_dict(xmind_file)
            
            # Convert xmindparser format to the format expected by xmind_to_testsuites
            converted_content = []
            for sheet in xmind_content_dict:
                converted_sheet = {
                    'title': sheet.get('title', 'Untitled'),
                    'topic': convert_xmindparser_topic(sheet.get('topic', {}))
                }
                converted_content.append(converted_sheet)
            
            logging.debug("Successfully parsed with xmindparser")
            testsuites = xmind_to_testsuites(converted_content)
            return testsuites
        except Exception as e:
            logging.warning("Failed to parse with xmindparser: %s, falling back to xmind library", e)
            # If xmind is not available, raise the error
            if not xmind:
                raise e
    
    # Fall back to original xmind library (for classic XMind format)
    if xmind:
        try:
            logging.info("Trying to parse with xmind library (for classic XMind format)")
            workbook = xmind.load(xmind_file)
            xmind_content_dict = workbook.getData()
            logging.debug("loading XMind file(%s) dict data: %s", xmind_file, xmind_content_dict)

            if xmind_content_dict:
                testsuites = xmind_to_testsuites(xmind_content_dict)
                return testsuites
            else:
                logging.error('Invalid XMind file(%s): it is empty!', xmind_file)
                return []
        except Exception as e:
            logging.error('Failed to parse XMind file(%s): %s', xmind_file, e)
            raise e
    else:
        # If both parsers fail, raise an error
        raise Exception("Failed to parse XMind file: Neither xmind nor xmindparser libraries could parse the file")

def convert_xmindparser_topic(topic):
    """Convert xmindparser topic format to the format expected by xmind_to_testsuites"""
    # 修复拼写错误：makers -> markers
    markers = []
    if isinstance(topic.get('markers'), list):
        markers = topic.get('markers')
    elif isinstance(topic.get('makers'), list):
        markers = topic.get('makers')  # 保持向后兼容
    
    converted = {
        'id': topic.get('id', ''),
        'title': topic.get('title', ''),
        'link': topic.get('link', None),
        'note': topic.get('note', None),
        'label': topic.get('label', None),
        'comment': topic.get('comment', None),  # 添加对comment的支持
        'markers': markers
    }
    
    # 增强日志记录，便于调试多层级结构
    logging.debug(f"Converting topic: {converted['title']} with {len(markers)} markers")
    
    # Convert subtopics recursively
    if 'topics' in topic and topic['topics']:
        converted['topics'] = []
        for subtopic in topic['topics']:
            converted['topics'].append(convert_xmindparser_topic(subtopic))
        logging.debug(f"Topic {converted['title']} has {len(converted['topics'])} subtopics")
    
    return converted


def get_xmind_testsuite_list(xmind_file):
    """Load the XMind file and get all testsuite in it

    :param xmind_file: the target XMind file
    :return: a list of testsuite data
    """
    xmind_file = get_absolute_path(xmind_file)
    logging.info('Start converting XMind file(%s) to testsuite data list...', xmind_file)
    testsuite_list = get_xmind_testsuites(xmind_file)
    suite_data_list = []

    for testsuite in testsuite_list:
        product_statistics = {'case_num': 0, 'non_execution': 0, 'pass': 0, 'failed': 0, 'blocked': 0, 'skipped': 0}
        for sub_suite in testsuite.sub_suites:
            suite_statistics = {'case_num': len(sub_suite.testcase_list), 'non_execution': 0, 'pass': 0, 'failed': 0, 'blocked': 0, 'skipped': 0}
            for case in sub_suite.testcase_list:
                if case.result == 0:
                    suite_statistics['non_execution'] += 1
                elif case.result == 1:
                    suite_statistics['pass'] += 1
                elif case.result == 2:
                    suite_statistics['failed'] += 1
                elif case.result == 3:
                    suite_statistics['blocked'] += 1
                elif case.result == 4:
                    suite_statistics['skipped'] += 1
                else:
                    logging.warning('This testcase result is abnormal: %s, please check it: %s', case.result, case.to_dict())
            sub_suite.statistics = suite_statistics
            for item in product_statistics:
                product_statistics[item] += suite_statistics[item]

        testsuite.statistics = product_statistics
        suite_data = testsuite.to_dict()
        suite_data_list.append(suite_data)

    logging.info('Convert XMind file(%s) to testsuite data list successfully!', xmind_file)
    return suite_data_list


def get_xmind_testcase_list(xmind_file):
    """Load the XMind file and get all testcase in it

    :param xmind_file: the target XMind file
    :return: a list of testcase data
    """
    xmind_file = get_absolute_path(xmind_file)
    logging.info('Start converting XMind file(%s) to testcases dict data...', xmind_file)
    testsuites = get_xmind_testsuites(xmind_file)
    testcases = []

    for testsuite in testsuites:
        product = testsuite.name
        for suite in testsuite.sub_suites:
            for case in suite.testcase_list:
                case_data = case.to_dict()
                case_data['product'] = product
                case_data['suite'] = suite.name
                testcases.append(case_data)

    logging.info('Convert XMind file(%s) to testcases dict data successfully!', xmind_file)
    return testcases


def xmind_testsuite_to_json_file(xmind_file):
    """Convert XMind file to a testsuite json file"""
    xmind_file = get_absolute_path(xmind_file)
    logging.info('Start converting XMind file(%s) to testsuites json file...', xmind_file)
    testsuites = get_xmind_testsuite_list(xmind_file)
    testsuite_json_file = xmind_file[:-6] + '_testsuite.json'

    if os.path.exists(testsuite_json_file):
        os.remove(testsuite_json_file)
        # logging.info('The testsuite json file already exists, return it directly: %s', testsuite_json_file)
        # return testsuite_json_file

    with open(testsuite_json_file, 'w', encoding='utf8') as f:
        f.write(json.dumps(testsuites, indent=4, separators=(',', ': '), ensure_ascii=False))
        logging.info('Convert XMind file(%s) to a testsuite json file(%s) successfully!', xmind_file, testsuite_json_file)

    return testsuite_json_file


def xmind_testcase_to_json_file(xmind_file):
    """Convert XMind file to a testcase json file"""
    xmind_file = get_absolute_path(xmind_file)
    logging.info('Start converting XMind file(%s) to testcases json file...', xmind_file)
    testcases = get_xmind_testcase_list(xmind_file)
    testcase_json_file = xmind_file[:-6] + '.json'

    if os.path.exists(testcase_json_file):
        os.remove(testcase_json_file)
        # logging.info('The testcase json file already exists, return it directly: %s', testcase_json_file)
        # return testcase_json_file

    with open(testcase_json_file, 'w', encoding='utf8') as f:
        f.write(json.dumps(testcases, indent=4, separators=(',', ': '), ensure_ascii=False))
        logging.info('Convert XMind file(%s) to a testcase json file(%s) successfully!', xmind_file, testcase_json_file)

    return testcase_json_file
