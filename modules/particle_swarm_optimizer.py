import sys
import numpy
from pyswarm import pso

from .strategy_simulator import StrategySimulator

'''
This class uses Particle Swarm Optimization in order to find the best investment strategy.
'''
class ParticleSwarmOptimizer:
    def __init__(self, data, fixed_parameters):
        self.data = data
        self.fixed_parameters = fixed_parameters
        # tweak parameters
        self.runs_per_strategy = 20
        self.swarmsize = 100
        self.maxiter = 5

    # perform Particle Swarm Optimization
    def optimize(self):
        # set lower bounds
        lower_bounds = [
            # target factor
            2,
            # maximum number of days before an ICO investment is harvested
            0,
            # minimum percentage to upgrade to next generation [%]
            70
        ]

        # set upper bounds
        upper_bounds = [
            # target factor
            10,
            # maximum number of days before an ICO investment is harvested
            60,
            # minimum percentage to upgrade to next generation [%]
            100
        ]

        # perform Particle Swarm Optimization
        print("Particle Swarm Optimization started")
        opt_parameters, inv_opt_profit = pso(self.inv_evaluate_multiple_runs, lower_bounds, upper_bounds,
            ieqcons=[], f_ieqcons=None, args=(), kwargs={},
            swarmsize=self.swarmsize, omega=0.5, phip=0.5, phig=0.5, maxiter=self.maxiter, minstep=1e-8,
            minfunc=1e-8, debug=True)

        # print results
        print("\nOPTIMAL STRATEGY PROFIT: $" + str(round(1.0 / inv_opt_profit)))
        print(opt_parameters)


    # return the inverse of the strategy profit
    def inv_evaluate(self, strategy):
        # add zero for spread increase
        strategy = [strategy[0], strategy[1], 0, strategy[2]]

        # run simulator
        simulator = StrategySimulator(self.data, self.fixed_parameters, False)

        # return inverse (since PSO minimizes the called function)
        return 1.0 / simulator.evaluate(strategy)


    # return the inverse of the minimum profit when the strategy is multiple times executed
    def inv_evaluate_multiple_runs(self, strategy):
        # add zero for spread increase
        strategy = [strategy[0], strategy[1], 0, strategy[2]]
        
        # run simulator multiple times
        profits = []
        for i in range(0, self.runs_per_strategy):
            simulator = StrategySimulator(self.data, self.fixed_parameters, False)
            profits.append(simulator.evaluate(strategy))            

        # use lowest profit to optimize for the worst case scenario
        lowest_profit = numpy.min(profits)

        # print status
        print(strategy)
        print("Strategy profit at least: $" + str(round(lowest_profit)))
        
        # return inverse (since PSO minimizes the called function)
        return 1.0 / max(lowest_profit, 1)