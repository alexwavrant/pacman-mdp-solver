# mdpAgents.py
# parsons/20-nov-2017
#
# Version 1
#
# The starting point for CW2.
#
# Intended to work with the PacMan AI projects from:
#
# http://ai.berkeley.edu/
#
# These use a simple API that allow us to control Pacman's interaction with
# the environment adding a layer on top of the AI Berkeley code.
#
# As required by the licensing agreement for the PacMan AI we have:
#
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
# 
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).

# The agent here is was written by Simon Parsons, based on the code in
# pacmanAgents.py
import math

from pacman import Directions
from game import Agent
import api
import random
import game
import util


class MDPAgent(Agent):

    # Constructor: this gets run when we first invoke pacman.py
    def __init__(self):
        #print "Starting up MDPAgent!"
        self.pacman = None
        self.width = None
        self.height = None
        self.corners = None
        self.walls = None
        self.food = None
        self.capsules = None
        self.ghosts = None
        self.ghostWithTimerLimit = None
        self.ghostStates = None
        self.worried = False

        self.legal = None

        self.currentMap = {}
        self.previousMap = {}

        # BEST SO FAR: self.REWARD = 0 / self.DISCOUNT_FACTOR = 0.7 / self.REWARD_FOOD = 1 / self.REWARD_GHOST = -2
        self.reward = 0
        self.discountFactor = 0.7
        self.foodReward = 1
        self.ghostReward = -2
        self.directions = ["North", "South", "West", "East"]

    # Gets run after an MDPAgent object is created and once there is
    # game state to access.
    def registerInitialState(self, state):
        print "Running registerInitialState for MDPAgent!"
        print "I'm at:"
        print api.whereAmI(state)

    # This is what gets run in between multiple games
    def final(self, state):
        print "Looks like the game just ended!"

    def getAction(self, state):
        self.updateEnvironmentInformation(state)
        states = self.getSetOfStates(self.width, self.height)
        self.currentMap = self.initStates(states)

        #self.printInformationBeforeUpdate()

        self.bellmanIteration()

        #self.printInformationAfterUpdate()

        # print("")
        # print("legal directions are: " + str(self.legal))

        pick = self.getBestDirection()
        # print("Pick is: " + str(pick))
        # print("\n\n")

        return api.makeMove(pick, self.legal)

    # STATES RELATED
    # @param width: width of the map
    # @param height: height of the map
    #
    #  @return: list of all possible states (squares) that either pacman or a ghost can be in
    def getSetOfStates(self, width, height):
        states = []
        for x in range(1, width - 1):
            for y in range(1, height - 1):
                if ((x, y) not in self.walls):  # and (x,y) not in self.food and (x,y) not in self.ghosts):
                    states.append((x, y))
        return states

    def initStates(self, states):
        statesInit = {}
        for state in states:
            statesInit[state] = self.reward
        return statesInit

    # @param state: a state (position) from the map
    #
    # @return reward: the rewards associated with the state input by the user
    def getRewardOfState(self, pose):
        reward = 0
        closestGhost = self.getClosestGhost(pose)
        indexClosestGhost = self.ghosts.index(closestGhost)
        distanceToClosestGhost = self.getDistanceToClosestGhost(pose, closestGhost)
        remaingTimeGhostEdible = self.ghostWithTimerLimit[indexClosestGhost][1]
        if (distanceToClosestGhost == 0):
            distanceToClosestGhost = 1

        # If a state is within a distance of 5 (mediumClassic map) or 2 (smallMDP map) from pacman, then the reward of that state
        # is going to be the reward of a ghost divided by the distance from this ghost
        # Example: state is at a distance of 2 square from pacman: Reward(state) = ghostReward / 2
        if (self.width > 10): # Goes here if the map is mediumClassic
            if (remaingTimeGhostEdible < 5 and distanceToClosestGhost < 5):
                self.ghostReward = -2
                reward += self.ghostReward / distanceToClosestGhost
            elif (remaingTimeGhostEdible > 5 and distanceToClosestGhost < 5):
                self.ghostReward = 2
                reward += self.ghostReward / distanceToClosestGhost
        else:  # Goes here if the map is smallGrid
            if (remaingTimeGhostEdible < 5 and distanceToClosestGhost < 2):
                self.ghostReward = -3 # 1595/2500 (0.64)
                #self.ghostReward = -2 # 1532/2500 (0.61)
                reward += self.ghostReward / distanceToClosestGhost


        if (pose in self.ghosts):
            if (remaingTimeGhostEdible < 4):
                reward += self.ghostReward

        if pose in self.food:
            reward += self.foodReward

        # If a ghost is not edible and is too close from pacman, then pacman should eat a capsule
        if (pose in self.capsules):
            if (self.shouldEatCapsule(pose, closestGhost, indexClosestGhost) == True):
                reward += 2
            else:
                reward += 1

        return reward

    # @param state: a state (position) from the map
    # @param pose: a position in the map
    #
    # @return: the utility of the state input by the user.
    def getUtility(self, pose):

        maxUtility = -1000
        for direction in self.directions:
            utility = self.getUtilityForward(pose, direction)
            utility += self.getUtilitySide(pose, Directions.LEFT[direction])
            utility += self.getUtilitySide(pose, Directions.RIGHT[direction])

            if utility > maxUtility:
                maxUtility = utility
        return maxUtility

    # @param pose: a position in the map
    # @param direction: the direction pacman wants to go to (80% of chance of success)
    #
    # @return utilityForward: the utility value if pacman successfully goes into the direction
    # input by the user
    def getUtilityForward(self, pose, direction):
        nextPose = self.getNextPose(pose, direction)
        if nextPose in self.walls:
            nextPose = pose

        # api.directionProb allows us to get the probability that a direction is going
        # to be executed as intended
        utilityForward = api.directionProb * self.previousMap[nextPose]
        return utilityForward

    # @param pose: a position in the map
    # @param direction: the direction pacman wants to go to (80% of chance of success)
    #
    # @return utilitySide: the utility value if pacman goes to the side of the desired direction
    def getUtilitySide(self, pose, direction):
        nextPose = self.getNextPose(pose, direction)
        if nextPose in self.walls:
            nextPose = pose

        # (1 - api.directionProb) / 2 allows us to get the probability that a direction is going
        # to be fail to be executed and that a side movement is executed instead.
        utilitySide = ((1 - api.directionProb) / 2) * self.previousMap[nextPose]
        return utilitySide

    def bellmanIteration(self):
        counter = 0

        while (self.currentMap != self.previousMap and counter < 20):
            counter = counter + 1
            self.previousMap = self.currentMap.copy()

            for state in self.previousMap:
                self.currentMap[state] = self.getRewardOfState(state) + (self.discountFactor * self.getUtility(state))
        #print (str(counter) + " iterations necessary")

    # @return bestDirection: The best direction pacman can goes to according to the optimal policy
    # we obtained from the MDP solver (the bellmanIteration() function)
    def getBestDirection(self):
        directions = {}

        for direction in self.legal:
            nextPose = self.getNextPose(self.pacman, direction)
            #print("   next pose: " + str(nextPose))
            directions[direction] = self.currentMap[nextPose]

        bestDirection = max(directions, key=directions.get)
        return bestDirection

    # @param state: the state of the game
    #
    # Update the information related to the environment
    # (e.g. pacman's position, corners, walls, food, ghosts, width, and height)
    def updateEnvironmentInformation(self, state):
        self.pacman = api.whereAmI(state)
        self.corners = api.corners(state)
        self.walls = api.walls(state)
        self.food = api.food(state)
        self.capsules = api.capsules(state)
        self.ghosts = api.ghosts(state)
        self.ghostStates = api.ghostStates(state)
        self.ghostWithTimerLimit = api.ghostStatesWithTimes(state)
        self.width = self.getLayoutWidth(self.corners)
        self.height = self.getLayoutHeight(self.corners)
        self.legal = api.legalActions(state)
        if Directions.STOP in self.legal:
            self.legal.remove(Directions.STOP)

    def getLayoutWidth(self, corners):
        width = -1
        for i in range(len(corners)):
            if corners[i][0] > width:
                width = corners[i][0]
        return width + 1

    def getLayoutHeight(self, corners):
        height = -1
        for i in range(len(corners)):
            if corners[i][1] > height:
                height = corners[i][1]
        return height + 1

    def getNextPose(self, currentPos, direction):
        if direction == Directions.NORTH:
            return (currentPos[0], currentPos[1] + 1)
        elif direction == Directions.SOUTH:
            return (currentPos[0], currentPos[1] - 1)
        elif direction == Directions.WEST:
            return (currentPos[0] - 1, currentPos[1])
        elif direction == Directions.EAST:
            return (currentPos[0] + 1, currentPos[1])

    def getGhostState(self, ghost):
        ghostState = [index for (index, test) in enumerate(self.ghostStates) if test[0] == ghost]
        return self.ghostStates[ghostState[0]][1]

    def getClosestGhost(self, pose):
        smallestDistance = 1000
        closestGhost = self.ghosts[0]
        for ghost in self.ghosts:
            distance = abs(ghost[1] - pose[1]) + abs(ghost[0] - pose[0])
            if (distance < smallestDistance):
                smallestDistance = distance
                closestGhost = ghost
        return closestGhost

    def getDistanceToClosestGhost(self, pose, closestGhost):
        return abs(closestGhost[1] - pose[1]) + abs(closestGhost[0] - pose[0])

    def isGhostScared(self, ghostIndex):
        if self.ghostStates[ghostIndex][1] == 0:
            return False

    def printInformationBeforeUpdate(self):

        print("ghost at:" + str(self.ghosts))
        print("ghosts states: " + str(self.ghostStates))
        print("pacman at:" + str(self.pacman))
        print("capsules at:" + str(self.capsules))
        print("number of food:" + str(len(self.food)) + "\n\n")
        print("current map before update:")
        print(self.currentMap)

    def printInformationAfterUpdate(self):
        print("\n current map updated:")
        print(self.currentMap)
        print("")

    # @param pose: current position of Pacman
    # @param: closesGhost: currnet position of the closest ghost to Pacman
    #
    # @return: True is pacman is close to a ghost and this ghost is not edible, false otherwise
    def shouldEatCapsule(self, SQUARE, closestGhost, indexClosestGhost):
        pacmanDistanceToClosestGhost = self.getDistanceToClosestGhost(self.pacman, closestGhost)
        # If pacman is close to a ghost and this ghost is not edible, then pacman should focus on eating a capsule
        if (pacmanDistanceToClosestGhost < 3 and self.isGhostScared(indexClosestGhost) == False):
            return True
        else:
            return False

    #################
    # GET FUNCTIONS #
    #################
