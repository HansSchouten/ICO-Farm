import sys
from pyswarm import pso

from .strategy_simulator import StrategySimulator

'''
This class uses Particle Swarm Optimization in order to find the best investment strategy.
'''
class ParticleSwarmOptimizer:
    def __init__(self, data, fixed_parameters):
        self.data = data
        self.fixed_parameters = fixed_parameters

    # perform Particle Swarm Optimization
    def optimize(self):
        # set lower bounds
        lower_bounds = [
            2,
            0,
            0,
            70
        ]

        # set upper bounds
        upper_bounds = [
            10,
            60,
            1,
            100
        ]

        # perform Particle Swarm Optimization
        print("Particle Swarm Optimization started")
        opt_parameters, inv_opt_profit = pso(self.inv_evaluate_multiple, lower_bounds, upper_bounds,
            ieqcons=[], f_ieqcons=None, args=(), kwargs={},
            swarmsize=500, omega=0.5, phip=0.5, phig=0.5, maxiter=5, minstep=1e-8,
            minfunc=1e-8, debug=True)

        # print results
        print(1.0 / inv_opt_profit)
        print(opt_parameters)


    # return the inverse of the strategy profit (since PSO minimizes the called function)
    def inv_evaluate(self, strategy):
        simulator = StrategySimulator(self.data, self.fixed_parameters, False)
        return 1.0 / simulator.evaluate(strategy)


    # return the inverse (since PSO minimizes the called function) of the minimum profit when the strategy is multiple times executed
    def inv_evaluate_multiple(self, strategy):
        lowest_profit = -1
        for i in range(0, 20):
            simulator = StrategySimulator(self.data, self.fixed_parameters, False)
            profit = simulator.evaluate(strategy)
            if lowest_profit < 0:
                lowest_profit = profit
            else:
                lowest_profit = min(lowest_profit, profit)
        print("$" + str(lowest_profit))
        print(strategy)
        return 1.0 / max(lowest_profit, 1)