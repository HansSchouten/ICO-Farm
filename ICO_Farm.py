import sys
import json
import csv
import math
import time
import numpy
from pathlib import Path
from pprint import pprint
from datetime import datetime

from modules.strategy_simulator_2017 import StrategySimulator2017
from modules.strategy_simulator import StrategySimulator
from modules.particle_swarm_optimizer import ParticleSwarmOptimizer

data = {}
fixed_parameters = [
    # start amount [usd]
    2000,
    # strategy start date
    '2017-05-01',
    # strategy end date
    '2018-01-18',
    # average ICO duration
    31,
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
    
    start_time = time.time()

    # uncomment desired method
    #averageFactorPerDuration(factors)
    manualStrategy()
    #particleSwarmOptimization()

    print("--- %s seconds ---" % (time.time() - start_time))


# manually test a strategy
def manualStrategy():
    global data
    global fixed_parameters

    results = []
    for i in range(0,1000):
        strategy = [
            # target factor
            2.5,
            # cashing timeout [days]
            7,
            # after cashing spread increase
            0,
            # minimum percentage to upgrade to next generation [%]
            92
        ]
        simulator = StrategySimulator(data, fixed_parameters, False)
        profit = simulator.evaluate(strategy)
        results.append(profit)

        print(str(i))
        print("min: $" + str(round(numpy.min(results))) + " median: $" + str(round(numpy.median(results))) + " average: $" + str(round(numpy.average(results))) + " max: $" + str(round(numpy.max(results))))
    print(sorted(results))

    
# perform Particle Swarm Optimization
def particleSwarmOptimization():
    global data
    global fixed_parameters

    optimizer = ParticleSwarmOptimizer(data, fixed_parameters)
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

        ico['ico_end_to_exchange_duration'] = getDuration(ico['end'], on_exchange_time)
        ico['on_exchange_time'] = on_exchange_time
        return ico, all_factors


# get number of days between two epoch timestamps
def getDuration(time1, time2):
    return math.floor(abs((time1 - time2) / 86400000))


# get the epoch version of the given date string
def dateToEpoch(date, format = '%Y-%m-%d'):
    return (datetime.strptime(date, format) - datetime(1970, 1, 1)).total_seconds() * 1000
    

# add a given number of days
def addDays(start, days):
    return math.floor(start + (days * 86400000))


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