import json
import csv
import sys
import math
from pathlib import Path
from pprint import pprint
from datetime import datetime
from pyswarm import pso

data = {}
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

def main():
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

    # manual test methods
    #averageFactorPerDuration(factors)

    # set data
    global data
    data['factors'] = factors
    data['icos'] = icos

    # perform Particle Swarm Optimization
    parameters = [
        # target factor
        3,
        # cashing timeout [days]
        50,
        # after cashing spread increase
        2,
        # minimum percentage to upgrade to next generation [%]
        95
    ]
    profit = evaluate(parameters)
    print(profit)


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


# add a given number of days
def addDays(start, days):
    return math.floor(start + (days * 86400000))


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


# evaluate a strategy
def evaluate(strategy):
    global data
    global fixed_parameters
    
    cash = fixed_parameters[0]
    current_day = dateToEpoch(fixed_parameters[1])
    end_day = dateToEpoch(fixed_parameters[2])
    investments = {}

    generation = 1
    generation_target = cash * strategy[0]
    generation_soft_target = generation_target * (strategy[3] / 100.0)
    generation_investment_amount = cash / fixed_parameters[4]

    while current_day < end_day:
        # harvest ICO investments
        for symbol in list(investments):
            investment = investments[symbol]
            if needsHarvest(investment, current_day, strategy):
                cash, investments = harvestInvestment(investments, cash, investment, current_day)

        # upgrade generation
        balance = cash + currentPortfolioValue(current_day, investments)
        if balance > generation_soft_target:
            generation += 1
            print("New generation: " + str(generation))
            generation_investment_amount = generation_target / (fixed_parameters[4] + ((generation - 1) * strategy[2]))
            generation_target = fixed_parameters[0] * math.pow(strategy[0], generation)
            generation_soft_target = generation_target * (strategy[3] / 100.0)

        # make new investments
        active_icos = activeICOs(current_day)
        if cash >= generation_investment_amount:
            old_len = len(investments)
            investments = makeInvestment(investments, generation_investment_amount, active_icos)
            # if an active ICO was found, decrease our cash
            if len(investments) > old_len:
                cash = cash - generation_investment_amount

        # increase durations of investments
        for symbol, investment in investments.items():
            if current_day > investment['on_exchange_time']:
                investment['duration'] += 1

        # go to bed and wait for next day
        current_day = addDays(current_day, 1)

    for symbol in list(investments):
        cash, investments = harvestInvestment(investments, cash, investments[symbol], current_day)

    return cash


# return wether the goal of this investment has been reached
def needsHarvest(investment, current_day, strategy):
    investment_value = getInvestmentValue(investment, current_day)
    target_factor = strategy[0]
    max_duration = strategy[1]

    # harvest profits after duration
    if investment['duration'] >= max_duration:
        return True

    # compute current target factor using linear decrease from {target_factor} to 1 in {max_duration} days
    current_target_factor = target_factor - (((target_factor - 1) * investment['duration']) / max_duration)

    # harvest profits after current target factor has been reached
    if (investment_value / investment['amount']) >= current_target_factor:
        return True

    return False


# close an investment
def harvestInvestment(investments, cash, investment, current_day):
    symbol = investment['symbol']
    newCash = getInvestmentValue(investment, current_day)
    cash += newCash
    del investments[symbol]
    print("Cashing investment " + symbol + " from $" + str(round(investment['amount'])) + " for $" + str(round(newCash))  + " after " + str(investment['duration']) + " days")
    return cash, investments


# make an investment
def makeInvestment(investments, generation_investment_amount, active_icos):
    for ico in active_icos:
        symbol = ico['symbol']
        if symbol in investments:
            continue
        investments[symbol] = {
            'symbol': symbol,
            'amount': generation_investment_amount,
            'duration': 0,
            'on_exchange_time': ico['on_exchange_time']
        }
        print("Adding investment " + symbol + " for $" + str(round(generation_investment_amount)))
        break
    
    return investments


# return current value of portfolio
def currentPortfolioValue(current_day, investments):
    value = 0

    for symbol, investment in investments.items():
        value += getInvestmentValue(investment, current_day)

    return value


# return the value of the given investment on the given day
def getInvestmentValue(investment, current_day):
    global data
    symbol = investment['symbol']
    ico = data['icos'][symbol]

    # factor equals 1 if the coin is not on the exchange yet
    if ico['on_exchange_time'] > current_day:
        return investment['amount']
    else:
        duration = getDuration(ico['on_exchange_time'], current_day)
        # return 0, in case there is no possibility to trade coin
        if duration not in data['factors'][symbol]:
            return 0
        factor = data['factors'][symbol][duration]
        return investment['amount'] * factor


# return the active ICOs
def activeICOs(current_date):
    global data
    global fixed_parameters

    icos = []
    max_ico_end_date = addDays(current_date, fixed_parameters[3])
    for symbol, ico in data['icos'].items():
        # if ICO is started and ICO is not ended
        if ico['end'] < max_ico_end_date and ico['end'] > current_date:
            icos.append({
                'symbol': symbol,
                'on_exchange_time': ico['on_exchange_time']
            })

    return icos


if __name__ == "__main__":
    main()