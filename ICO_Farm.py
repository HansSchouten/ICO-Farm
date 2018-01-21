import sys
import json
import csv
import math
from pathlib import Path
from pprint import pprint
from datetime import datetime

from modules.strategy_simulator import StrategySimulator
from modules.particle_swarm_optimizer import ParticleSwarmOptimizer

data = {}
logging_enabled = True
fixed_parameters = [
    # start amount [usd]
    2000,
    # strategy start date
    '2017-05-01',
    # strategy end date
    '2018-01-18',
    # average ICO duration
    21,
    # start spread factor
    5
]


# main method
def main():
    global data

    icos = {}
    factors = {}
    
    with open('data/past-icos.csv') as csvfile:
        reader = csv.DictReader(csvfile)
        for ico in reader:
            symbol = ico['symbol']
            if ico['end'] == '':
                continue
            ico['end'] = dateToEpoch(ico['end'])
            ico, factors = processICO(ico, factors)
            if ico != False:
                icos[symbol] = ico

    # set data
    data['factors'] = factors
    data['icos'] = icos
    
    # uncomment desired method
    #averageFactorPerDuration(factors)
    #manualStrategy()
    particleSwarmOptimization()


# manually test a strategy
def manualStrategy():
    global data
    global fixed_parameters
    global logging_enabled

    strategy = [
        # target factor
        2.38,
        # cashing timeout [days]
        6,
        # after cashing spread increase
        0,
        # minimum percentage to upgrade to next generation [%]
        92
    ]
    simulator = StrategySimulator(data, fixed_parameters, logging_enabled)
    profit = simulator.evaluate(strategy)
    print(profit)

    
# perform Particle Swarm Optimization
def particleSwarmOptimization():
    global data
    global fixed_parameters

    simulator = StrategySimulator(data, fixed_parameters, False)
    optimizer = ParticleSwarmOptimizer(simulator)
    optimizer.optimize()


# process the given ICO and store for each duration the achieved factor
def processICO(ico, all_factors):
    if ico['ico_token_price'] == '':
        return False, all_factors
    
    symbol = ico['symbol']
    data_file_path = Path('data/' + symbol + '.json')
    if not data_file_path.is_file():
        return False, all_factors
    
    on_exchange_time = 0
    start_value = float(ico['ico_token_price'])

    with open(data_file_path) as data_file:
        data = json.load(data_file)
        factors = {}
        
        # find moment on which the coin is published to an exchange
        for tuple in data['market_cap_by_available_supply']:
            time = tuple[0]
            price = float(tuple[1])

            # skip to the moment there is a marketcap
            if price > 0:
                on_exchange_time = time
                break

        # if coin is not on exchange yet, return
        if on_exchange_time == 0:
            return False, all_factors

        # find all factors
        for tuple in data['price_usd']:
            time = tuple[0]
            price = float(tuple[1])

            # skip to the moment the coin was on an exchange
            if time > on_exchange_time:
                duration = getDuration(on_exchange_time, time)
                factor = round(price / start_value, 1)

                # replace factor if needed
                if duration in factors:
                    if factor > factors[duration]:
                        factors[duration] = factor
                else:
                    factors[duration] = factor
            
            # add factors to all factors
            all_factors[symbol] = factors

        ico['on_exchange_time'] = on_exchange_time
        return ico, all_factors


# get number of days between two epoch timestamps
def getDuration(time1, time2):
    return math.floor(abs((time1 - time2) / 86400000))


# get the epoch version of the given date string
def dateToEpoch(date, format = '%Y-%m-%d'):
    return (datetime.strptime(date, format) - datetime(1970, 1, 1)).total_seconds() * 1000


# compute the average profit factor for each duration
def averageFactorPerDuration(all_factors):
    counts = {}
    sums = {}

    for symbol, factors in all_factors.items():
        for duration, factor in factors.items():
            if duration in counts:
                counts[duration] += 1
                sums[duration] += factor
            else:
                counts[duration] = 1
                sums[duration] = factor

    averages = {}
    for duration in counts:
        if counts[duration] > 5:
            averages[duration] = str(sums[duration] / counts[duration]) + ' - ' + str(counts[duration])

    pprint(averages)


if __name__ == "__main__":
    main()