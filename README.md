# LogStream Worker Group with Autoscaling Scale Down Hooks 

This solution borrows HEAVILY from the [AWS EC2 Autoscaling Group Examples](https://github.com/aws-samples/amazon-ec2-auto-scaling-group-examples) repo. This repo has two different examples of running a LogStream Worker Group with LifeCycle hooks to delay scale down when persistent queues are active.

## The Problem...

If you're using the persistent queueing feature in LogStream, while using an Autoscaling Group, you have the risk of data loss in a scenario where Autoscaling tries to scale down your ASG while there is backpressure from one or more destinations. Since queueing is done locally to the worker node, if the node is terminated (and the EBS volume destroyed), any data in the queue will be lost. 

This repo creates a solution that attempts to "buy time" in the case of a scale down event, to allow time to try and repair the destination system and allow the queue to clear out prior to shutdown.  

## The Approach

AWS EC2 Autoscaling has a mechanism that allows you to insert a Lifecycle Hook into the Autoscaling lifecycle - you can have a hook during a scale up event before an instance is launched, or you can have a hook during a scale down event before the instance is terminated. This approach inserts a Termination lifecycle event hook which checks for the existence of files in one or more queue directories. If there are files in the queue directories, it delays the termination by a specified amount of time (theoretically up to 48 hours). 

The LifeCycle hook mechanism that this approach does not allow cancellation of termination event, only delaying the termination, hopefully providing enough time to *fix* the destination that is queueing. As such, in no way does it guarantee no data loss, it simply buys time. 

For more info on Autoscaling Lifecycle Hooks, see the AWS documentation at [https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html](https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html).

## Options

This repo has two example version of the approach:

* [lambda-managed-linux](lambda-managed-linux) uses a Lambda Function to handle the lifecycle hook and SSM to connect to the instance in question to check the queue directories.

* [ec2-managed-linux](ec2-managed-linux) uses a small EC2 instance running a script every minute via crontab to check for lifecycle hook events, and SSM to connect to the instance in question to check the queue directories.

## License

As this is built on the AWS examples in the [AWS EC2 Autoscaling Group Examples](https://github.com/aws-samples/amazon-ec2-auto-scaling-group-examples) repo, it follows the same license, which is as follows:

```
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
 ```