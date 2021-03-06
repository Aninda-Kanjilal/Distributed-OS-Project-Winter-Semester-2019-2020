"""Example demonstrating the use of Troupes to parallelize computation
for long-running actors.  The example uses a horrible, exponential
growth function as the "doing work" portion and demonstrates both a
non-troupe and troupe implementation, with both sequential and
parallel submissions.

This can be simply run via: $ python fibactor.py

"""


from thespian.actors import *
from thespian.troupe import troupe
from timer import timeit
from datetime import timedelta

# Specify a deadman timeout: give up on waiting for a response after
# this period of time.
max_wait = timedelta(seconds=60)



def multi(n):
    l=[]
    for i in range(1,11):
        l.append(n*i)
    return l


# Simple Actor which takes a number and responds with the Multiple
# value for that number.

class Multiple(ActorTypeDispatcher):
    def receiveMsg_int(self, intval, sender):
        self.send(sender, multi(intval))


# Same as the simple actor above, but this is decorated to allow a
# Troupe of 10 actors automatically.

@troupe(10)
class MultipleT(ActorTypeDispatcher):
    def receiveMsg_int(self, intval, sender):
        self.send(sender, multi(intval))


# Sends input and waits for output one at a time.

def serial_test(asys, Mult, inputs):
    for N in inputs:
        print(asys.ask(Mult, N, max_wait))
    asys.tell(Mult, ActorExitRequest())

def parallel_test(asys, Mult, inputs):
    for N in inputs:
        asys.tell(Mult, N)
    for R in range(len(inputs)):
        print(asys.listen(max_wait))
    asys.tell(Mult, ActorExitRequest())


# Actual tests, with timing output

@timeit
def t1(asys, inputs):
    serial_test(asys, asys.createActor(Multiple), inputs)

@timeit
def t2(asys, inputs):
    parallel_test(asys, asys.createActor(Multiple), inputs)

@timeit
def t3(asys, inputs):
    serial_test(asys, asys.createActor(MultipleT), inputs)


@timeit
def t4(asys, inputs):
    parallel_test(asys, asys.createActor(MultipleT), inputs)


if __name__ == "__main__":
    asys = ActorSystem('multiprocTCPBase')
    inputs= tuple([eval(x) for x in input("Enter the values separated by commas : ").split(',')])
    print('Asking a single actor, one at a time...')
    # This will ask a single actor serially and is generally
    # unsurprising in behavior.
    t1(asys, inputs)

    print('Sending all requests to the single actor, then getting responses...')
    # This sends all the requests to a single actor and then waits for
    # the responses.  This works, but some of the responses are
    # delayed or appear to be "batched" up.  This is because actors
    # send and receive messages asynchronously, but in the
    # multiprocTCPBase, that asynchronous code is not running while
    # the actor itself is processing.  There are pros and cons to
    # this, but one of the results is the irregular response
    # generation because the sends are "paused" while the actor is
    # busy computing a fibonacci value.
    t2(asys, inputs)

    print('Sending all requests to a troupe, one at a time...')
    # This again is unsurprising: since requests are only sent one at
    # a time, there is only one actor ever used, and there are no
    # benefits to having a troupe.  This mainly shows that the troupe
    # performs normally in the simple case.
    t3(asys, inputs)

    print('Sending all requests to a troupe, then getting responses...')
    # This is where the benefits of a troupe are observable.  The
    # number of actors in the troupe is greater than the set of
    # inputs, so all values are computed in parallel (and the only
    # change needed was to add the decorator to the actor).  The
    # parallelism can be observed by seeing the results printed in
    # order of (transmit+computation) cost and not just submission
    # order.
    t4(asys, inputs)

    asys.shutdown()

# Things to try:
#  * Change the inputs array to add more or less
#  * Change the troupe parameters to specify different minimum and maximum numbers.
#  * Try more inputs than there are troupe members
#  * Change the system base:
#     * multiprocTCPBase
#     * multiprocUDPBase
#     * multiprocQueuebase
#     * simpleSystemBase  (note: not parallel, no speedups)
