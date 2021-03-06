## A generalizable model of spike-timing dependent plasticity for the the Neural Simulation Tool ([NEST](https://github.com/nest/nest-simulator))

This is a bachelor graduation project carried out at the [Laboratory of Computational Neuroscience](http://lcn1.epfl.ch) 
from [Swiss Institute of Technology in Lausanne](http://www.epfl.ch). It was supervised by 
[Alex Seeholzer](https://github.com/flinz) during fall semester 2015.

Project's goal was to evaluate how can spike-timing dependent plasticity (STDP) mechanisms be implemented in the NEST 
simulator, allowing complex protocols and neuro-modulation definitions.

Standard approach, using NEST-native synapse system:

- synapse updates happen only on pre-synaptic spikes
- delays are complex to manage correctly
- limited access on post-synaptic variables
- no neuro-modulation
- directly available out of the box
- minimum delay is resolution
- theoretically complete graph scales at **O(n^2)** connections for **n** neurons

Neuron entity approach, using a fake neuron as a synapse:

- synapses has its own dynamics (calibrate/update/handle)
- delays are manage by the simulation
- all variables are located in the synapse
- neuro-modulation through custom event
- require a DSL (pynest) or must follow a well defined *contract* (pre-neuron -> synapse, synapse -> post-neuron, post-neuron -> synapse on port **1** for feedback)
- minimum delay is twice the resolution
- theoretically complete graph scales at **O(4n^2)** connections for **n** neurons

### In this repository

- standard approach (root): 
    - triplet model (Pfister 2006), `stdp_triplet_all_in_one_synapse` is defined inside `stdp_triplet_connection.h` (difference with NEST 2.10 `stdp_synapse` is variables centralization)
- neuron entity approach (root):
    - triplet model (Pfister 2006), `stdp_triplet_neuron` is defined inside `stdp_triplet_neuron.{h,cpp}`
    - long-stability model (Zenke 2015), `stdp_long_neuron` is defined inside `stdp_long_neuron.{h,cpp}` (no tests)
- tests:
    - triplet model (Pfister 2006) both approach (classical tests as well as visual decays tests)
- slides: [reveal.js](https://github.com/hakimel/reveal.js/) midterm and final presentations
- pynest:
    - neuron entity approach DSL example (do not handle all connections types, i.e. no indegree)
- examples:
    - standard approach for triplet model (Pfister 2006) pairing experiment
    - neuron entity approach with contract for triplet model (Pfister 2006) pairing experiment
    - neuron entity approach with dsl for triplet model (Pfister 2006) pairing experiment
    - Zenke entity approach with contract for long-stability model (Zenke 2015) pairing experiment (but different parameters)
- benchmarks:
    - a Brunnel balanced network with delta neuron (`iaf_psc_deta`): static connections vs standard approach vs neuron entity approach (through different network orders and cores)
    - a feedforward (**n** pre-synaptic neurons connected to **1** post-synpatic neuron): static connections vs standard approach vs neuron entity approach (through different **n**, cores and resolutions)
    - some installations scripts for NEST and this module
    - a command `./clusterify.py` for building easily NEST clusters (simulation via MPI) on [DigitalOcean](https://www.digitalocean.com)
    - plotting scripts of benchmark results
- plots: all plotted results
    
### How to install this module

NEST simulator >= 2.8.0 is required (not tested below) before proceeding to further step. 
Otherwise please check out the official installation [steps](http://www.nest-simulator.org/installation/).

```bash
git clone https://github.com/zifeo/nest-stdpmodule.git stdpmodule
cd stdpmodule
./bootstrap.sh
./configure
make
make install
cd ..
rm -rf stdpmodule
```

### Domain specific language (DSL)

All content of pynest folder will be copied to nest installation folder and automatically available through python.
However depending on your installation it must sometimes be manually done (check last lines of `make install`).

The DSL offers the following facilities:

- `nest.helloSTDP()`: start this module and patch pynest accordingly
- `triplet_synapse = nest.Connect(pre, post, conn_spec = None, syn_spec = None, model = "stdp_triplet_neuron", pre_syn_spec = None, syn_post_spec = None)`: connect `pre` and `post` neurons through triplet model (Pfister 2006) and return associated neuron entity synapses 
- `nest.Spikes(neurons, times)`: send on-demand spikes to `neurons` at given range `times`

### Cluster Beowulf

Requires at least python 2.7 and DigitalOcean [python-bindings](https://github.com/koalalorenzo/python-digitalocean) (`pip install -U python-digitalocean`).
The deloy system was tested up to **1/2** million neurons (Brunnel balanced network) on **400**vcpus with **1.28**To RAM for ~19$ hourly.
This script is provided as is and comes with no warranty nor liability.

The command offers the following facilities:

- `./clusterify.py key [token]`: setup Digital Ocean token (empty for removing it)
- `./clusterify.py list`: list current cluster
- `./clusterify.py create [2|3|...] [1gb|2gb|...]`: create n-cluster of given size and setup ssh everywhere
- `./clusterify.py install [script]`: execute given bash script on each node
- `./clusterify.py run [1..] [program]`: run given python program on the cluster using mpi and n processes
- `./clusterify.py delete`: delete: remove current cluster

Common scenario (global installation takes 15 minutes on average):

```bash
./clusterify.py key digitalOceanToken
./clusterify.py create 4 8gb
./clusterify.py list
./clusterify.py install install_env.bash
./clusterify.py install install_nest.bash
./clusterify.py install install_stdpmodule.bash
./clusterify.py run 16 brunnel.py
./clusterify.py run 8 brunnel.py
./clusterify.py run 4 brunnel.py
./clusterify.py delete`
```

### Taranis

Independly from this project, [Taranis](https://github.com/zifeo/Taranis) is a related short proof of concept aiming to evaluate how can the [actor model](https://en.wikipedia.org/wiki/Actor_model) be implemented with STDP.
Using abstract "dynamics" (calibrate/update/handle) as building block, a neuron is composed three parts:

- post-connection dynamics: each incoming event will be arriving to the neuron through there
- neuron dynamics: care about post and pre calibrations and updates as well as its own dynamics
- pre-connection dynamics: each outgoing event will be leaving the neuron through there

All of those components can interact with each others and are including inside the same actor. 
Each event sent will be broadcasted to the neuron's successors as well as neuron's priors. 
Even though not everything above was implemented and tuned due to lack of time, Taranis can provide some insights for further work.
Performance are quite good for a few neurons but does not scale well due in part to JVM garbage collection.

### Benchmarks results

All the benchmarks were run **5** times on the same configuration (duration/precision compromise, some of them took hours to be completed).

#### Brunnel balanced network

Using delta neuron (`iaf_psc_deta`).

![](./plots/brunnel-per-approach.png)
![](./plots/brunnel-per-order.png)

#### Feedforward

**n** pre-synaptic neurons connected to **1** post-synpatic neuron.

![](./plots/feedforward-per-approach-0.1ms.png)
![](./plots/feedforward-per-approach-0.5ms.png)
![](./plots/feedforward-per-approach-1ms.png)

### License

All the work is provided under NEST [GNU General Public License 2 or later](http://www.nest-simulator.org/license/) and respectively DigitalOcean agreements.
See `LICENSE` for further details.

### References

- Eppler, Jochen Martin et al.. (2015). NEST 2.8.0.
- F. Zenke, E.J. Agnes and W. Gerstner, Diverse synaptic plasticity mechanisms orchestrated to form and retrieve memories in spiking neural networks, Nature Communications, Vol. 6, Nr. 6922, 2015.
- F. Zenke and W. Gerstner, Limits to high-speed simulations of spiking neural networks using general-purpose computers, Frontiers in neuroinformatics, Vol. 8, pp. 76, 2014.
- J.P. Pfister and W. Gerstner, Triplets of Spikes in a Model of Spike Timing-Dependent Plasticity, J. Neuroscience, Vol. 26, Nr. 38, pp. 9673-9682, 2006.
