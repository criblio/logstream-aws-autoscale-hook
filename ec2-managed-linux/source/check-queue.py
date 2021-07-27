#!/usr/bin/env python3
# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import boto3
import os
import json
import logging
import time
import sys

from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

autoscaling = boto3.client('autoscaling')
ssm = boto3.client('ssm')
sqs = boto3.client('sqs')


def send_lifecycle_action(event, result):
    try:
        response = autoscaling.complete_lifecycle_action(
            LifecycleHookName=event['LifecycleHookName'],
            AutoScalingGroupName=event['AutoScalingGroupName'],
            LifecycleActionToken=event['LifecycleActionToken'],
            LifecycleActionResult=result,
            InstanceId=event['EC2InstanceId']
        )

        logger.info(response)
    except ClientError as e:
        message = 'Error completing lifecycle action: {}'.format(e)
        logger.error(message)
        raise Exception(message)

    return

def run_command(event, command):

    # Run Command
    logger.info('Calling SendCommand: {} for instance: {}'.format(command, event['EC2InstanceId']))
    attempt = 0
    while attempt < 10:
        attempt = attempt + 1
        try:
            time.sleep(5 * attempt)
            logger.info('SendCommand, attempt #: {}'.format(attempt))
            response = ssm.send_command(
                InstanceIds=[event['EC2InstanceId']],
                DocumentName='AWS-RunShellScript',
                Parameters={
                    'commands': [
                        command
                    ]
                }
            )

            logger.info(response)
            if 'Command' in response:
                break

            if attempt == 10:
                message = 'Command did not execute succesfully in time allowed.'
                raise Exception(message)

        except ClientError as e:
            message = 'Error calling SendCommand: {}'.format(e)
            logger.error(message)
            continue

    # Check Command Status
    command_id = response['Command']['CommandId']
    logger.info('Calling GetCommandInvocation for command: {} for instance: {}'.format(command_id, event['EC2InstanceId']))
    attempt = 0

    while attempt < 20:
        attempt = attempt + 1
        try:
            time.sleep(5 * attempt)
            logger.info('GetCommandInvocation, attempt #: {}'.format(attempt))
            result = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=event['EC2InstanceId'],
            )
            if result['Status'] == 'InProgress':
                logger.info('Command is running.')
                continue
            elif result['Status'] == 'Success':
                logger.info('Command completed successfully: {}'.format(result['StandardOutputContent']))
                break
            elif result['Status'] == 'Failed':
                message = 'Command did not execute successfully: {}'.format(e)
                logger.error(message)
                raise Exception(message)
            else:
                message = 'Command has an unhandled status, will continue: {}'.format(e)
                logger.warning(message)
                continue
        except ssm.exceptions.InvocationDoesNotExist as e:
            message = 'Error calling GetCommandInvocation: {}'.format(e)
            logger.error(message)
            raise Exception(message)

    if result['Status'] == 'Success':
        return
    else:
        message = 'Command did not execute succesfully in time allowed.'
        raise Exception(message)

def main():


    if "QUEUE_URL" not in os.environ:
      logger.error("No QUEUE_URL defined, exiting")
      sys.exit(255)

    sqsret = sqs.receive_message(QueueUrl=os.environ['QUEUE_URL'])
    if 'Messages' in sqsret:
      for message in sqsret['Messages']:
        event = json.loads(message['Body'])

        logger.info(event)
        # If Instance is Launching into AutoScalingGroup
        if event['Origin'] == 'AutoScalingGroup' and event['Destination'] == 'EC2':
            logger.info('Instance Terminating in AutoScalingGroup')
            try:
                command = "QUEUES='%s' /opt/cribl/scripts/check_files.sh" % os.environ['QUEUES']
                run_command(event, command)
                send_lifecycle_action(event, 'CONTINUE')
            except Exception as e:
                logger.error("Exception Failure")
                logger.info('Execution Complete')
            delres = sqs.delete_message(QueueUrl=os.environ['QUEUE_URL'], ReceiptHandle=message['ReceiptHandle'])
            logger.info(delres)
            next
        else:
          logger.info("Not the right Event Type - ignoring")
          delres = sqs.delete_message(QueueUrl=os.environ['QUEUE_URL'], ReceiptHandle=message['ReceiptHandle'])
          logger.info(delres)

        # Else
        #logger.info('An unhandled lifecycle action occured, abandoning.')
        ##send_lifecycle_action(event, 'ABANDON')
        #logger.info('Execution Complete')
        #delres = sqs.delete_message(QueueUrl=os.environ['QUEUE_URL'], ReceiptHandle=message['ReceiptHandle'])
        #logger.info(delres)

      # End
    return

main()