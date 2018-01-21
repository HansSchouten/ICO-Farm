from pyswarm import pso

from .strategy_simulator import StrategySimulator

'''
This class uses Particle Swarm Optimization in order to find the best investment strategy.
'''
class ParticleSwarmOptimizer:
    def __init__(self, simulator: StrategySimulator, logging_enabled: bool):
        self.simulator = simulator
        self.simulator.disableLogging()
        self.logging_enabled = logging_enabled

    # perform Particle Swarm Optimization
    def optimize(self):
        # set lower bounds
        lower_bounds = [
            1.5,
            0,
            0,
            60
        ]

        # set upper bounds
        upper_bounds = [
            15,
            60,
            3,
            120
        ]

        # perform Particle Swarm Optimization
        print("Particle Swarm Optimization started")
        opt_parameters, inv_opt_profit = pso(self.simulator.inv_evaluate, lower_bounds, upper_bounds,
            ieqcons=[], f_ieqcons=None, args=(), kwargs={},
            swarmsize=500, omega=0.5, phip=0.5, phig=0.5, maxiter=5, minstep=1e-8,
            minfunc=1e-8, debug=self.logging_enabled)

        # print results
        print(1.0 / inv_opt_profit)
        print(opt_parameters)