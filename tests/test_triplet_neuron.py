import nest
import unittest
from math import exp

@nest.check_stack
class STDPTripletNeuronTestCase(unittest.TestCase):
    """Check stdp_triplet_neuron model properties."""

    @classmethod
    def setUpClass(self):
        nest.Install("stdpmodule")

    def setUp(self):
        nest.set_verbosity('M_WARNING')
        nest.ResetKernel()

        # settings
        self.dendritic_delay = 1.0
        self.decay_duration = 5.0
        self.syn_spec = {
            "weight": 5.0,
            "Wmax": 100.0,
            "tau_plus": 16.8,
            "tau_plus_triplet": 101.0,
            "tau_minus": 33.7,
            "tau_minus_triplet": 125.0,
            "Aplus": 0.1,
            "Aminus": 0.1,
            "Aplus_triplet": 0.1,
            "Aminus_triplet": 0.1,
            "Kplus": 0.0,
            "Kplus_triplet": 0.0,
            "Kminus": 0.0,
            "Kminus_triplet": 0.0,
            "nearest_spike": False,
        }

        # setup basic circuit
        self.pre_neuron = nest.Create("parrot_neuron")
        self.post_neuron = nest.Create("parrot_neuron")
        self.triplet_synapse = nest.Create("stdp_triplet_neuron", params = self.syn_spec)

        nest.Connect(self.pre_neuron, self.triplet_synapse)
        nest.Connect(self.triplet_synapse, self.post_neuron, syn_spec = {
            "receptor_type": 1,
            "delay": self.dendritic_delay
        }) # do not repeat spike
        nest.Connect(self.post_neuron, self.triplet_synapse, syn_spec = {
            "receptor_type": 1
        }) # differentiate post-synaptic feedback

    def generateSpikes(self, neuron, times):
        """Trigger spike to given neuron at specified times."""
        delay = 1.0
        gen = nest.Create("spike_generator", 1, { "spike_times": [t - delay for t in times] })
        nest.Connect(gen, neuron, syn_spec = { "delay": delay })

    def status(self, which):
        """Get synapse parameter status."""
        return nest.GetStatus(self.triplet_synapse, [which])[0][0]

    def decay(self, time, Kplus, Kplus_triplet, Kminus, Kminus_triplet):
        """Decay variables."""
        Kplus *= exp(- time / self.syn_spec["tau_plus"])
        Kplus_triplet *= exp(- time / self.syn_spec["tau_plus_triplet"])
        Kminus *= exp(- time / self.syn_spec["tau_minus"])
        Kminus_triplet *= exp(- time / self.syn_spec["tau_minus_triplet"])
        return (Kplus, Kplus_triplet, Kminus, Kminus_triplet)

    def facilitate(self, w, Kplus, Kminus_triplet):
        """Facilitate weight."""
        return w + Kplus * (self.syn_spec["Aplus"] + self.syn_spec["Aplus_triplet"] * Kminus_triplet)

    def depress(self, w, Kminus, Kplus_triplet):
        """Depress weight."""
        return w - Kminus * (self.syn_spec["Aminus"] + self.syn_spec["Aminus_triplet"] * Kplus_triplet)

    def assertAlmostEqualDetailed(self, expected, given, message):
        """Improve assetAlmostEqual with detailed message."""
        messageWithValues = "%s (expected: `%s` was: `%s`" % (message, str(expected), str(given))
        self.assertAlmostEqual(given, expected, msg = messageWithValues)


    def test_badPropertiesSetupsThrowExceptions(self):
        """Check that exceptions are thrown when setting bad parameters."""
        def setupProperty(property):
            bad_syn_spec = self.syn_spec.copy()
            bad_syn_spec.update(property)
            self.triplet_synapse = nest.Create("stdp_triplet_neuron", params = bad_syn_spec)

        def badPropertyWith(content, parameters):
            self.assertRaisesRegexp(nest.NESTError, "BadProperty(.+)" + content, setupProperty, parameters)

        badPropertyWith("Kplus", { "Kplus": -1.0 })
        badPropertyWith("Kplus_triplet", { "Kplus_triplet": -1.0 })
        badPropertyWith("Kminus", { "Kminus": -1.0 })
        badPropertyWith("Kminus_triplet", { "Kminus_triplet": -1.0 })

    def test_varsZeroAtStart(self):
        """Check that pre and post-synaptic variables are zero at start."""
        self.assertAlmostEqualDetailed(0.0, self.status("Kplus"), "Kplus should be zero")
        self.assertAlmostEqualDetailed(0.0, self.status("Kplus_triplet"), "Kplus_triplet should be zero")
        self.assertAlmostEqualDetailed(0.0, self.status("Kminus"), "Kminus should be zero")
        self.assertAlmostEqualDetailed(0.0, self.status("Kminus_triplet"), "Kminus_triplet should be zero")

    def test_preVarsIncreaseWithPreSpike(self):
        """Check that pre-synaptic variables (Kplus, Kplus_triplet) increase after each pre-synaptic spike."""

        self.generateSpikes(self.pre_neuron, [2.0])

        Kplus = self.status("Kplus")
        Kplus_triplet = self.status("Kplus_triplet")

        nest.Simulate(2.0 + self.dendritic_delay)
        self.assertAlmostEqualDetailed(Kplus + 1.0, self.status("Kplus"), "Kplus should have increased by 1")
        self.assertAlmostEqualDetailed(Kplus_triplet + 1.0, self.status("Kplus_triplet"),
                                       "Kplus_triplet should have increased by 1")

    def test_postVarsIncreaseWithPostSpike(self):
        """Check that post-synaptic variables (Kminus, Kminus_triplet) increase after each post-synaptic spike."""

        self.generateSpikes(self.post_neuron, [2.0])

        Kminus = self.status("Kminus")
        Kminus_triplet = self.status("Kminus_triplet")

        nest.Simulate(2.0 + self.dendritic_delay)
        self.assertAlmostEqualDetailed(Kminus + 1.0, self.status("Kminus"), "Kminus should have increased by 1")
        self.assertAlmostEqualDetailed(Kminus_triplet + 1.0, self.status("Kminus_triplet"),
                                       "Kminus_triplet should have increased by 1")

    def test_preVarsDecayAfterPreSpike(self):
        """Check that pre-synaptic variables (Kplus, Kplus_triplet) decay after each pre-synaptic spike."""

        self.generateSpikes(self.pre_neuron, [2.0])

        (Kplus, Kplus_triplet, _, _) = self.decay(self.decay_duration, 1.0, 1.0, 0.0, 0.0)

        nest.Simulate(2.0 + self.decay_duration + self.dendritic_delay)
        self.assertAlmostEqualDetailed(Kplus, self.status("Kplus"), "Kplus should have decay")
        self.assertAlmostEqualDetailed(Kplus_triplet, self.status("Kplus_triplet"), "Kplus_triplet should have decay")

    def test_preVarsDecayAfterPostSpike(self):
        """Check that pre-synaptic variables (Kplus, Kplus_triplet) decay after each post-synaptic spike."""

        self.generateSpikes(self.pre_neuron, [2.0])
        self.generateSpikes(self.post_neuron, [3.0, 4.0])

        (Kplus, Kplus_triplet, _, _) = self.decay(self.decay_duration, 1.0, 1.0, 0.0, 0.0)

        nest.Simulate(2.0 + self.decay_duration + self.dendritic_delay)
        self.assertAlmostEqualDetailed(Kplus, self.status("Kplus"), "Kplus should have decay")
        self.assertAlmostEqualDetailed(Kplus_triplet, self.status("Kplus_triplet"), "Kplus_triplet should have decay")

    def test_postVarsDecayAfterPreSpike(self):
        """Check that post-synaptic variables (Kminus, Kminus_triplet) decay after each pre-synaptic spike."""

        self.generateSpikes(self.post_neuron, [2.0])

        (_, _, Kminus, Kminus_triplet) = self.decay(self.decay_duration, 0.0, 0.0, 1.0, 1.0)

        nest.Simulate(2.0 + self.decay_duration + self.dendritic_delay)
        self.assertAlmostEqualDetailed(Kminus, self.status("Kminus"), "Kminus should have decay")
        self.assertAlmostEqualDetailed(Kminus_triplet, self.status("Kminus_triplet"),
                                       "Kminus_triplet should have decay")

    def test_postVarsDecayAfterPostSpike(self):
        """Check that post-synaptic variables (Kminus, Kminus_triplet) decay after each post-synaptic spike."""

        self.generateSpikes(self.post_neuron, [2.0, 3.0, 4.0])

        (_, _, Kminus, Kminus_triplet) = self.decay(1.0, 0.0, 0.0, 1.0, 1.0)
        Kminus += 1.0
        Kminus_triplet += 1.0

        (_, _, Kminus, Kminus_triplet) = self.decay(1.0, 0.0, 0.0, Kminus, Kminus_triplet)
        Kminus += 1.0
        Kminus_triplet += 1.0

        (_, _, Kminus, Kminus_triplet) = self.decay(self.decay_duration - 2.0, 0.0, 0.0, Kminus, Kminus_triplet)

        nest.Simulate(2.0 + self.decay_duration + self.dendritic_delay)
        self.assertAlmostEqualDetailed(Kminus, self.status("Kminus"), "Kminus should have decay")
        self.assertAlmostEqualDetailed(Kminus_triplet, self.status("Kminus_triplet"),
                                       "Kminus_triplet should have decay")

    def test_weightChangeWhenPrePostSpikes(self):
        """Check that weight changes whenever a pre-post spike pair happen."""

        self.generateSpikes(self.pre_neuron, [2.0])
        self.generateSpikes(self.post_neuron, [4.0])

        Kplus = self.status("Kplus")
        Kplus_triplet = self.status("Kplus_triplet")
        Kminus = self.status("Kminus")
        Kminus_triplet = self.status("Kminus_triplet")
        weight = self.status("weight")

        (Kplus, Kplus_triplet, Kminus, Kminus_triplet) = self.decay(2.0, Kplus, Kplus_triplet, Kminus, Kminus_triplet)
        weight = self.depress(weight, Kminus, Kplus_triplet)
        Kplus += 1.0
        Kplus_triplet += 1.0

        (Kplus, Kplus_triplet, Kminus, Kminus_triplet) = self.decay(2.0, Kplus, Kplus_triplet, Kminus, Kminus_triplet)
        weight = self.facilitate(weight, Kplus, Kminus_triplet)

        nest.Simulate(20.0)
        self.assertAlmostEqualDetailed(weight, self.status("weight"), "weight should have decreased")

    def test_weightChangeWhenPrePostPreSpikes(self):
        """Check that weight changes whenever a pre-post-pre spike triplet happen."""

        self.generateSpikes(self.pre_neuron, [2.0, 6.0])
        self.generateSpikes(self.post_neuron, [4.0])

        Kplus = self.status("Kplus")
        Kplus_triplet = self.status("Kplus_triplet")
        Kminus = self.status("Kminus")
        Kminus_triplet = self.status("Kminus_triplet")
        weight = self.status("weight")

        (Kplus, Kplus_triplet, Kminus, Kminus_triplet) = self.decay(2.0, Kplus, Kplus_triplet, Kminus, Kminus_triplet)
        weight = self.depress(weight, Kminus, Kplus_triplet)
        Kplus += 1.0
        Kplus_triplet += 1.0

        (Kplus, Kplus_triplet, Kminus, Kminus_triplet) = self.decay(2.0, Kplus, Kplus_triplet, Kminus, Kminus_triplet)
        weight = self.facilitate(weight, Kplus, Kminus_triplet)
        Kminus += 1.0
        Kminus_triplet += 1.0

        (Kplus, Kplus_triplet, Kminus, Kminus_triplet) = self.decay(2.0, Kplus, Kplus_triplet, Kminus, Kminus_triplet)
        weight = self.depress(weight, Kminus, Kplus_triplet)

        nest.Simulate(20.0)
        self.assertAlmostEqualDetailed(weight, self.status("weight"), "weight should have decreased")

    def test_nearestSpike(self):
        nest.SetStatus(self.triplet_synapse, params = { "nearest_spike": True })

        self.generateSpikes(self.pre_neuron, [2.0, 3.0, 4.0])
        self.generateSpikes(self.post_neuron, [2.0, 3.0, 4.0])

        nest.Simulate(4.0)

        self.assertAlmostEqualDetailed(1.0, self.status("Kplus"), "state should saturate")
        self.assertAlmostEqualDetailed(1.0, self.status("Kplus_triplet"), "state should saturate")
        self.assertAlmostEqualDetailed(1.0, self.status("Kminus"), "state should saturate")
        self.assertAlmostEqualDetailed(1.0, self.status("Kminus_triplet"), "state should saturate")

    def test_maxWeightStaturatesWeight(self):
        """Check that setting maximum weight property keep weight limited."""

        limited_weight = self.status("weight") + 1e-10
        nest.SetStatus(self.triplet_synapse, params = { "Wmax": limited_weight })

        self.generateSpikes(self.pre_neuron, [2.0])

        nest.Simulate(3.0)
        self.assertAlmostEqualDetailed(limited_weight, self.status("weight"), "weight should have been limited")

    def test_minWeightStaturatesWeight(self):
        """Check that setting maximum weight property keep weight limited."""

        limited_weight = self.status("weight")
        nest.SetStatus(self.triplet_synapse, params = { "Wmin": limited_weight })

        self.generateSpikes(self.pre_neuron, [2.0])

        nest.Simulate(2.0)
        self.assertAlmostEqualDetailed(limited_weight, self.status("weight"), "weight should have been limited")


def suite():
    suite1 = unittest.TestLoader().loadTestsFromTestCase(STDPTripletNeuronTestCase)
    return unittest.TestSuite([suite1])

def run():
    runner = unittest.TextTestRunner(verbosity = 2)
    runner.run(suite())

if __name__ == "__main__":
    run()
