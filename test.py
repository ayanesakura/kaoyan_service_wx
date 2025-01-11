import requests
from flask import Flask, request, jsonify
import os
import json
from wxcloudrun.utils.file_util import download_file_from_wxcloud



if __name__ == '__main__':
    download_file_from_wxcloud('cloud://prod-0g0dkv502d54c928.7072-prod-0g0dkv502d54c928-1330319089/resumes/1728558883057.pdf', 'wxcloudrun/resumes')