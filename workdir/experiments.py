#!/usr/bin/env python3

import os
import sys
import subprocess
import logging
from datetime import datetime


class Path():
    @staticmethod
    def join(path, *elements):
        joinedPath = path[0:-1] if path.endswith("/") else path
        for element in elements:
            normalizedElment = element[0:-1] if element.endswith("/") else element
            normalizedElment = normalizedElment[1:] if normalizedElment.startswith("/") else normalizedElment
            joinedPath += "/" + normalizedElment
        return joinedPath

class Command():
    def __init__(self, command):
        self.command = command

    def run(self, ignoreErrors=False):
        logging.debug(f"Executing command : '{self.command}'")

        ret = subprocess.run(self.command.split(), capture_output=True)

        error = ret.stderr.decode("utf-8")
        if(error and not ignoreErrors):
            raise Exception(error)

        output = ret.stdout.decode("utf-8")
        if(output):
            logging.debug(f"Output: '{output}'")
            return output

        return ""

class Experiment():
    def __init__(self, path):
        self.path = path
        self.testsPath = Path.join(path, "tests")
        self.algorithmsPath = Path.join(path, "algorithms")
        self.resultsPath = Path.join(path, "results")

    def runTests(self, rundir, checker, keepIndividualResultFiles=False):
        self.archivePreviousResults(self.resultsPath)

        for algorithm in self.getAlgorithms():
            logging.info(f"Run {algorithm} with {checker.getName()}")

            rundir.clear()
            binary = self.getBinaryForAlgorithm(algorithm)
            binary.compileTo(rundir.getPath())
            self.copyTestsTo(rundir.getTestsPath())

            createdResults = self.createTestResultsPath(algorithm, checker.getName())
            self.summaryFile = Path.join(createdResults, "summary.csv")
            self.clearCreatedResultsDir(createdResults)

            numberOfTests = self.getNumberOfTests()
            for testNumber in range(numberOfTests):
                #if(testNumber>10): break
                rundir.prepareDataForTestNo(testNumber)
                rundir.cleanQilingLog()
                performanceData = checker.run(4600, 10000000000, 1000000000)
                rundir.keepTestOutput(testNumber)
                rundir.keepPerformanceData(performanceData, testNumber)
                rundir.copyTestResultsTo(createdResults, testNumber)
                rundir.copyQilingLog(createdResults, testNumber, checker.getName())
                self.verifyTestResult(createdResults, testNumber, performanceData.get('returned_code'))
                self.updateSummary(createdResults, testNumber, checker.getName())
                self.removeOrKeepIndividualResultFiles(createdResults, keepIndividualResultFiles)
                rundir.copyTestLog(createdResults, testNumber, checker.getName())
                rundir.cleanTestLog()
                if(performanceData.get('returned_code') != '0'):
                    break
            
    def copyTestsTo(self, destinationPath):
        for test in Command(f"ls -f {self.testsPath}").run().split("\n"):
            if(test.strip() and test.strip().endswith(".in")):
                Command(f"cp {Path.join(self.testsPath,test)} {destinationPath}").run()

    def getAlgorithms(self):
        return [algorithm for algorithm in Command(f"ls -lf {self.algorithmsPath}").run().split("\n") if(algorithm and algorithm.endswith(".cpp"))]

    def getBinaryForAlgorithm(self, algorithm):
        return Binary(Path.join(self.algorithmsPath, algorithm))

    def getNumberOfTests(self):
        return len([i for i in Command(f"ls -f {self.testsPath}").run().split("\n") if i.endswith(".in")])

    def createTestResultsPath(self, algorithm, checkerName):
        return Path.join(self.resultsPath, algorithm.split("/")[-1] + "-" + checkerName)

    def archivePreviousResults(self, createdResults):
        archive = f'{createdResults}_{datetime.now().strftime("%Y_%m_%d_%H_%M_%S")}'
        Command(f"cp -r {createdResults} {archive}").run(ignoreErrors=True)
        Command(f"rm -rf {createdResults}").run(ignoreErrors=True)

    def clearCreatedResultsDir(self, createdResults):
        Command(f"rm -rf {createdResults}").run()
        Command(f"mkdir -p {createdResults}").run()
        with open(self.summaryFile, "w") as f:
            f.write("TestNumber;ExecutionTime;ExecutedSteps;PeakMemoryUsage;CorrectAnswer\n")

    def verifyTestResult(self, createdResults, testNumber, returnCode):
        if(returnCode != '0'):
            if(returnCode == None):
                returnCode = '-1'
            diff = returnCode
        elif(os.path.exists(f"{Path.join(self.testsPath, f'{testNumber}.out')}")):
            diff = Command(f"git diff -G.* --no-index \
                {Path.join(self.testsPath, f'{testNumber}.out')} \
                {Path.join(createdResults, f'{testNumber}.out')}").run()
        else:
            diff = "missing output"
        with open(f"{Path.join(createdResults, f'{testNumber}.compare')}", "w") as f:
            f.write(diff)

    def updateSummary(self, createdResults, testNumber, checkerName):
        with open(self.summaryFile, "a") as f:
            time = None
            if(os.path.exists(f"{createdResults}/{testNumber}.time")):
                with open(f"{createdResults}/{testNumber}.time", "r") as t:
                    time = t.read()
            steps = None
            if(os.path.exists(f"{createdResults}/{testNumber}.steps")):
                with open(f"{createdResults}/{testNumber}.steps", "r") as s:
                    steps = s.read()
            memory = None
            if(os.path.exists(f"{createdResults}/{testNumber}.memory")):
                with open(f"{createdResults}/{testNumber}.memory", "r") as m:
                    memory = m.read()
            compare = None
            if(os.path.exists(f"{createdResults}/{testNumber}.compare")):
                with open(f"{createdResults}/{testNumber}.compare", "r") as c:
                    compare = c.read()
            if(compare == ""):
                correct = 1
            elif(compare == "missing output" or len(compare)<10):
                correct = compare
            elif(compare and compare!=""):
                correct = 0
            else:
                correct = -2

            dataRecord = f"{testNumber}"
            if(time != None):
                dataRecord += f";{time}"
            else: 
                dataRecord += f";NA"
            if(steps != None):
                dataRecord += f";{steps}"
            else: 
                dataRecord += f";NA"
            if(memory != None):
                dataRecord += f";{memory}"
            else: 
                dataRecord += f";NA"
            if(correct != None):
                dataRecord += f";{correct}"
            else:
                dataRecord += f";NA"
            dataRecord += "\n"
            f.write(dataRecord)

    def removeOrKeepIndividualResultFiles(self, createdResults, keep):
        if(not keep):
            for file in Command(f"ls -p {createdResults}").run().split("\n"):
                if(file.strip() 
                    and not file.strip().endswith(".txt")
                    and not file.strip().endswith(".csv")):
                    Command(f"rm -f {Path.join(createdResults, file)}").run()


class Rundir():
    def __init__(self, path):
        self.path = path
        self.testsPath = path + "/tests"

    def clear(self):
        Command(f"rm -rf {self.path}").run()
        Command(f"mkdir -p {self.testsPath}").run()

    def prepareDataForTestNo(self, testNumber):
        Command(f"cp {self.testsPath}/{testNumber}.in {self.testsPath}/in.txt").run()

    def keepTestOutput(self, testNumber):
        if(os.path.exists(f"{self.testsPath}/out.txt")):
            Command(f"cp {self.testsPath}/out.txt {self.testsPath}/{testNumber}.out").run()
            Command(f"rm {self.testsPath}/out.txt").run()

    def keepPerformanceData(self, performanceDataDic, testNumber):
        if(performanceDataDic.get("steps")):
            with open(f"{Path.join(self.testsPath, f'{testNumber}.steps')}", "w") as f:
                f.write(performanceDataDic['steps'])
        
        timeSystem = 0
        timeUser = 0
        if(performanceDataDic.get("time_system")):
            timeSystem = performanceDataDic.get("time_system")
        if(performanceDataDic.get("time_user")):
            timeUser = performanceDataDic.get("time_user")
        if(performanceDataDic.get("time_system") or performanceDataDic.get("time_user")):
            with open(f"{Path.join(self.testsPath, f'{testNumber}.time')}", "w") as f:
                f.write(str(max(float(timeSystem), float(timeUser))))
        
        if(performanceDataDic.get("memory_usage")):
            with open(f"{Path.join(self.testsPath, f'{testNumber}.memory')}", "w") as f:
                f.write(performanceDataDic['memory_usage'])

    def copyTestResultsTo(self, path, testNumber):
        for testResult in Command(f"ls -f {self.testsPath}").run().split("\n"):
            if(testResult.strip().endswith(f"{testNumber}.out")
                    or testResult.strip().endswith(f"{testNumber}.steps")
                    or testResult.strip().endswith(f"{testNumber}.time")
                    or testResult.strip().endswith(f"{testNumber}.memory")):
                Command(f"cp {Path.join(self.testsPath, testResult.strip())} {path}").run()

    def copyQilingLog(self, path, testNumber, checkerName):
        if(os.path.exists(self.path+"/qiling-log.txt")):
            with open(self.path+"/qiling-log.txt", "r") as log:
                with open(path+"/qiling-log.txt", "a") as savedLog:
                    savedLog.write(f"----------- {testNumber} {checkerName}\n")
                    savedLog.write(log.read())

    def copyTestLog(self, path, testNumber, checkerName):
        if(os.path.exists("/code/workdir/test-log.txt")):
            with open("/code/workdir/test-log.txt", "r") as log:
                with open(path+"/test-log.txt", "a") as savedLog:
                    savedLog.write(f"----------- {testNumber} {checkerName}\n")
                    savedLog.write(log.read())

    def cleanTestLog(self):
        if(os.path.exists("/code/workdir/test-log.txt")):
            with open("/code/workdir/test-log.txt", "w") as f:
                f.write("")

    def cleanQilingLog(self):
        if(os.path.exists(self.path+"/qiling-log.txt")):
            Command(f"rm -f {self.path}/qiling-log.txt").run()

    def getPath(self):
        return self.path

    def getTestsPath(self):
        return self.testsPath


class Binary():
    def __init__(self, path):
        self.path = path

    def compileTo(self, destinationPath):
        Command(f"g++ -O0 {self.path} -o {Path.join(destinationPath,'a.out')}").run()


class Checker():
    def parseMetaOutput(self, meta):
        try:
            return dict(
                filter(
                    lambda x: len(x) > 1,
                    map(lambda x: x.split(': ', 1), meta.strip().split('\n')),
                )
            )
        except Exception as e:
            raise e


class TimeChecker(Checker):

    def getName(self):
        return "time-checker"

    def run(self, maxTime, maxMemory, maxOutputSize):
        return self.parseMetaOutput(
            Command(f"./workdir/test -s {maxMemory} -h {maxMemory} -t {maxTime} -o {maxOutputSize}").run()
            )


class StepsChecker(Checker):

    def getName(self):
        return "steps-checker"

    def run(self, maxTime, maxMemory, maxOutputSize):
        return self.parseMetaOutput(
            Command(f"./workdir/test.py -s {maxMemory} -h {maxMemory} -t {maxTime} -o {maxOutputSize}").run()
            )