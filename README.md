# k-Means Maximum Entropy Exploration

https://arxiv.org/abs/2205.15623

## To install

Experimental framework and PyTorch KME
```
pip install -r requirements.txt
# will install torchkme from GitHub or manually:
# cd kme.all/kme.py && pip install -e .
```

C++ KME implementation and experiments
```
cd kme.all/kme.cpp && make && pip install -e .
```

## Repo structure

#### `framework`
- a simple framework to explore and play
- implements manifolds to run experiments

#### `kme.all/kme.cpp`
- a C++ implementation of KME
- a Python wrapped library for the C++ implementation
- code to reproduce entropy experiments

#### `kme.all/kme.py`
- Python package of PyTorch KME implementation

#### `mujoco`
- code to reproduce experiments in mujoco envs


## Experiments

To run entropy experiments, use the compiled binary kme/entropy. To see options
```
./entropy --help  
```

To run exploration experiments, use the script mujoco/train.py. You must install the modified stable-baselines3 repository found in mujoco/libs. The script requires the environment variable DEVICE to set the PyTorch device. To see options

```
python train.py --help
```

Please refer to the paper for parameter values. 

# To-Dos

- [x] Handle batches in online kmeans (w/ shuffling) @ap
- [x] Add initialization techniques to kmeans @ap
- [x] Implement Density, OnlineEstimators and KMeans @ap
- [x] Optimize calls for batches and matmuls @ap
- [x] Fix bug of point spwaning at (0) in viz @xan
- [x] Write down skeleton of rl experiment script @xan
- [x] Restructure repository according to rl exp @both
- [x] Fix logic flaw on kmeans encoder for distances @ap
- [x] dataset: if n(samples) < 2: dont train @ap
- [] bring out the device, dtype, seed @ap
- [] use camel case convention for filenames @ap
- [] (future) kmeans estimator: add interpolate function @ap
- [] change logic for the sequential rewards @ap
- [] add function to parallelize @ap
- [] add learned distance in update_distances <= @ap
- [] pathological: first_mask FALSE AND closest_idx @ap
- [] infer_batch, call twice the min @ap
- [] pairwise_distance optimization @ap
- [] port distances stuff into kmeans_estimator @ap
- [] Reorder manifolds classes @xan
- [] Add online knn density estimator @ap
- [] Fix vizualizer to handle any np.array shape @xan
- [] Lay down clear plan for all experiments in paper @both

