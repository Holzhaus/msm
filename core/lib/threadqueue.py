#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import abc
import threading
import queue
from dbus.mainloop.glib import threads_init
class AbstractQueue:
    """
    Usage:
        class InheritedQueue(AbstractQueue):
            def _create_thread(self):
                return InheritedQueueThread()
        q = InheritedQueue()
        q.put_multiple(obj)
        q.start()
        while not q.work_finished:
            # Blocking 'get' from a Queue.
            output = q.get()
            print(output)
        q.join()
    """
    __metaclass__ = abc.ABCMeta
    def __init__( self, num_worker_threads=4 ):
        # Create a single input and a single output queue for all threads.
        self._input_queue = queue.Queue()
        self._output_queue = queue.Queue()
        self._work_left = 0 # How much work is left
        self._work_started = 0
        # Create the "thread pool"
        self._pool = []
        for i in range( num_worker_threads ):
            thread = self._create_thread()
            thread.set_input_queue( self._input_queue )
            thread.set_output_queue( self._output_queue )
            self._pool.append( thread )
    @abc.abstractmethod
    def _create_thread( self ):
        pass
    @property
    def work_left( self ):
        return self._work_left
    @property
    def work_started( self ):
        return self._work_started
    @property
    def work_done( self ):
        return ( self.work_started - self.work_left )
    def start( self ):
        self._work_started = self._work_left
        # Start all threads
        for thread in self._pool:
            thread.start()
    def put( self, obj ):
        """
        Puts an input object into the input queue. The object will be passed to the worker threads.
        """
        self._input_queue.put( obj )
        self._work_left += 1
    def put_multiple( self, obj_list ):
        """
        Convenience method put multiple inputs into the input queue at once (preserving the order).
        """
        for obj in obj_list:
            self.put( obj )
    def get( self ):
        """
        Gets an output from the output_queue.
        Returns:
            the next output from the output queue
        """
        obj = self._output_queue.get()
        self._work_left -= 1
        return obj
    def join( self ):
        """
        Ask threads to die and wait for them to do it
        """
        for thread in self._pool:
            thread.join()
class AbstractQueueThread( threading.Thread ):
    """ A worker thread that takes directory names from a queue, finds all
        files in them recursively and reports the result.

        Input is done by placing directory names (as strings) into the
        Queue passed in dir_q.

        Output is done by placing tuples into the Queue passed in result_q.
        Each tuple is (thread name, dirname, [list of files]).

        Ask the thread to stop by calling its join() method.
    """
    __metaclass__ = abc.ABCMeta
    def __init__( self ):
        super().__init__()
        self._input_queue = None
        self._output_queue = None
        self._stoprequest = threading.Event()
    @abc.abstractmethod
    def work( self, input_obj ):
        pass
    def set_input_queue( self, input_queue ):
        if self._input_queue is not None:
            raise RuntimeWarning( 'thread {} already has an input queue'.format( self ) )
        self._input_queue = input_queue
    def set_output_queue( self, output_queue ):
        if self._output_queue is not None:
            raise RuntimeWarning( 'thread {} already has an output queue'.format( self ) )
        self._output_queue = output_queue
    def run( self ):
        # As long as we weren't asked to stop, try to take new tasks from the
        # queue. The tasks are taken with a blocking 'get', so no CPU
        # cycles are wasted while waiting.
        # Also, 'get' is given a timeout, so stoprequest is always checked,
        # even if there's nothing in the queue.
        while not self._stoprequest.isSet():
            try:
                input_obj = self._input_queue.get( True, 0.05 )
            except queue.Empty:
                continue
            else:
                output_obj = self.work( input_obj )
                self._output_queue.put( output_obj )
    def join( self, timeout=None ):
        self._stoprequest.set()
        super().join( timeout )
class QueueWatcherThread( threading.Thread ):
    __metaclass__ = abc.ABCMeta
    def __init__( self, q ):
        super().__init__()
        self._queue = q
    @property
    def work_left( self ):
        return self._queue.work_left
    @property
    def work_started( self ):
        return self._queue.work_started
    @property
    def work_done( self ):
        return self._queue.work_done
    def run( self ):
        self.on_start( self.work_left )
        self._queue.start()
        output_list = []
        while self.work_left:
            # Blocking 'get' from a Queue.
            output = self._queue.get()
            output_list.append( output )
            self.on_output( self.work_left, output )
        self._queue.join()
        self.on_finished( output_list )
    def on_start( self, work_left ):
        pass
    def on_output( self, work_left, output ):
        pass
    def on_finished( self, output_list ):
        pass
