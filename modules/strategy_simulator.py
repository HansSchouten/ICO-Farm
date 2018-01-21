import math
import time
import random
import sys
from datetime import datetime

'''
This class can simulate possible investment strategies.
'''
class StrategySimulator:
    def __init__(self, data, fixed_parameters, logging_enabled):
        self.data = data
        self.fixed_parameters = fixed_parameters
        self.logging_enabled = logging_enabled
        self.past_icos = {}


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
            self.log("\n" + time.strftime('%Y-%m-%d', time.localtime(current_day/1000)))

            # harvest ICO investments
            for symbol in list(investments):
                investment = investments[symbol]
                if self.needsHarvest(investment, current_day, strategy):
                    cash, investments = self.harvestInvestment(investments, cash, investment, current_day)
            
            # upgrade generation
            balance = cash + self.currentPortfolioValue(current_day, investments)
            if balance > generation_soft_target:
                generation += 1
                self.log("\nGENERATION " + str(generation))
                generation_investment_amount = generation_target / (self.fixed_parameters[4] + ((generation - 1) * strategy[2]))
                generation_target = self.fixed_parameters[0] * math.pow(strategy[0], generation)
                generation_soft_target = generation_target * (strategy[3] / 100.0)
                
            # make new investments
            while cash >= generation_investment_amount:
                investments = self.makeInvestment(investments, generation_investment_amount)
                cash -= generation_investment_amount

            # increase durations of investments
            for symbol, investment in investments.items():
                if investment['days_until_on_exchange'] == 0:
                    investment['duration'] += 1
                else:
                    investment['days_until_on_exchange'] -= 1
                   
            # log current status
            self.log("Cash: $" + str(round(cash)))
            self.log("Portfolio: $" + str(round(self.currentPortfolioValue(current_day, investments))))

            # go to bed and wait for next day
            current_day = self.addDays(current_day, 1)
            
        # revert to yesterday and add values of currently open investments
        current_day = self.addDays(current_day, -1)
        for symbol, investment in investments.items():
            cash += self.getInvestmentValue(investment)

        return cash


    # return wether the goal of this investment has been reached
    def needsHarvest(self, investment, current_day, strategy):
        investment_value = self.getInvestmentValue(investment)
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
        newCash = self.getInvestmentValue(investment)
        cash += newCash
        del investments[symbol]
        self.log("Cashing investment " + symbol + " from $" + str(round(investment['amount'])) + " for $" + str(round(newCash))  + " after " + str(investment['duration']) + " days on exchange")
        return cash, investments


    # make an investment
    def makeInvestment(self, investments, generation_investment_amount):
        not_used_icos = [x for x in self.data['icos'] if x not in self.past_icos]
        if len(not_used_icos) == 0:
            return investments

        symbol = random.choice(not_used_icos)
        self.past_icos[symbol] = 1

        ico = self.data['icos'][symbol]
        # ico end date to exchange duration + some random days from investment until the end of the ICO
        days_until_on_exchange = ico['ico_end_to_exchange_duration'] + random.randint(2, 7)
        investments[symbol] = {
            'symbol': symbol,
            'amount': generation_investment_amount,
            'duration': 0,
            'days_until_on_exchange': days_until_on_exchange
        }
        self.log("Adding investment " + symbol + " for $" + str(round(generation_investment_amount)) + " on exchange over " + str(ico['ico_end_to_exchange_duration']) + " (+" + str(days_until_on_exchange - ico['ico_end_to_exchange_duration']) + ") days")
    
        return investments


    # return current value of portfolio
    def currentPortfolioValue(self, current_day, investments):
        value = 0

        for symbol, investment in investments.items():
            value += self.getInvestmentValue(investment)

        return value


    # return the value of the given investment on the given day
    def getInvestmentValue(self, investment):
        symbol = investment['symbol']
        ico = self.data['icos'][symbol]

        # factor equals 1 if the coin is not on the exchange yet
        if investment['days_until_on_exchange'] > 0:
            return investment['amount']
        else:
            duration = investment['duration']
            # return 0, in case there is no possibility to trade coin
            if duration not in self.data['factors'][symbol]:
                return 0
            factor = self.data['factors'][symbol][duration]
            return investment['amount'] * factor


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