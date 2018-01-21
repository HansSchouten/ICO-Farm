import sys
import math
from pprint import pprint
from datetime import datetime

'''
This class represents a possible strategy.
'''
class StrategySimulator:
    def __init__(self, data, fixed_parameters, logging_enabled):
        self.data = data
        self.fixed_parameters = fixed_parameters
        self.logging_enabled = logging_enabled


    # return the inverse of the strategy profit (since PSO minimizes the called function)
    def inv_evaluate(self, strategy):
        return 1.0 / evaluate(strategy)


    # evaluate a strategy
    def evaluate(self, strategy):
        # round strategy parameters if needed
        strategy[1] = round(strategy[1])
        strategy[2] = round(strategy[2])
    
        cash = self.fixed_parameters[0]
        current_day = self.dateToEpoch(self.fixed_parameters[1])
        end_day = self.dateToEpoch(self.fixed_parameters[2])
        investments = {}

        generation = 1
        generation_target = cash * strategy[0]
        generation_soft_target = generation_target * (strategy[3] / 100.0)
        generation_investment_amount = cash / self.fixed_parameters[4]

        while current_day < end_day:
            # harvest ICO investments
            for symbol in list(investments):
                investment = investments[symbol]
                if self.needsHarvest(investment, current_day, strategy):
                    cash, investments = self.harvestInvestment(investments, cash, investment, current_day)

            # upgrade generation
            balance = cash + self.currentPortfolioValue(current_day, investments)
            if balance > generation_soft_target:
                generation += 1
                self.log("\nNew generation: " + str(generation))
                generation_investment_amount = generation_target / (self.fixed_parameters[4] + ((generation - 1) * strategy[2]))
                generation_target = self.fixed_parameters[0] * math.pow(strategy[0], generation)
                generation_soft_target = generation_target * (strategy[3] / 100.0)

            # make new investments
            active_icos = self.activeICOs(current_day)
            if cash >= generation_investment_amount:
                old_len = len(investments)
                investments = self.makeInvestment(investments, generation_investment_amount, active_icos)
                # if an active ICO was found, decrease our cash
                if len(investments) > old_len:
                    cash = cash - generation_investment_amount

            # increase durations of investments
            for symbol, investment in investments.items():
                if current_day > investment['on_exchange_time']:
                    investment['duration'] += 1

            # go to bed and wait for next day
            current_day = self.addDays(current_day, 1)

        for symbol in list(investments):
            cash, investments = self.harvestInvestment(investments, cash, investments[symbol], current_day)

        return cash


    # return wether the goal of this investment has been reached
    def needsHarvest(self, investment, current_day, strategy):
        investment_value = self.getInvestmentValue(investment, current_day)
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
    def harvestInvestment(self, investments, cash, investment, current_day):
        symbol = investment['symbol']
        newCash = self.getInvestmentValue(investment, current_day)
        cash += newCash
        del investments[symbol]
        self.log("Cashing investment " + symbol + " from $" + str(round(investment['amount'])) + " for $" + str(round(newCash))  + " after " + str(investment['duration']) + " days")
        return cash, investments


    # make an investment
    def makeInvestment(self, investments, generation_investment_amount, active_icos):
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
            self.log("Adding investment " + symbol + " for $" + str(round(generation_investment_amount)))
            break
    
        return investments


    # return current value of portfolio
    def currentPortfolioValue(self, current_day, investments):
        value = 0

        for symbol, investment in investments.items():
            value += self.getInvestmentValue(investment, current_day)

        return value


    # return the value of the given investment on the given day
    def getInvestmentValue(self, investment, current_day):
        symbol = investment['symbol']
        ico = self.data['icos'][symbol]

        # factor equals 1 if the coin is not on the exchange yet
        if ico['on_exchange_time'] > current_day:
            return investment['amount']
        else:
            duration = self.getDuration(ico['on_exchange_time'], current_day)
            # return 0, in case there is no possibility to trade coin
            if duration not in self.data['factors'][symbol]:
                return 0
            factor = self.data['factors'][symbol][duration]
            return investment['amount'] * factor


    # return the active ICOs
    def activeICOs(self, current_date):
        icos = []
        max_ico_end_date = self.addDays(current_date, self.fixed_parameters[3])
        for symbol, ico in self.data['icos'].items():
            # if ICO is started and ICO is not ended
            if ico['end'] < max_ico_end_date and ico['end'] > current_date:
                icos.append({
                    'symbol': symbol,
                    'on_exchange_time': ico['on_exchange_time']
                })

        return icos

    # log message to console, if logging is enabled
    def log(self, message):
        if self.logging_enabled:
            print(message)


    # get number of days between two epoch timestamps
    def getDuration(self, time1, time2):
        return math.floor(abs((time1 - time2) / 86400000))


    # get the epoch version of the given date string
    def dateToEpoch(self, date, format = '%Y-%m-%d'):
        return (datetime.strptime(date, format) - datetime(1970, 1, 1)).total_seconds() * 1000
    

    # add a given number of days
    def addDays(self, start, days):
        return math.floor(start + (days * 86400000))