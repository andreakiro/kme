import numpy as np
import scipy
import gymnasium
from ..density import Density
from ..geometry import Geometry

# TODO. Sampling multiple points in one call for Euclidean and Spherical.
# TODO. Proper implementation of hypersphere and torus (support d!=2 and use multiple charts to avoid singularities.
# TODO. Fix sampling in torus.
# TODO. Confirm distance function on torus.
# TODO. Bug with point in center of torus.
# TODO. Rename classes.

def standardize_angle(x):
  x = x % (2 * np.pi)
  if x < 0:
    x += 2 * np.pi
  return x

def modular_distance(x, y, m):
  d = 0
  for _x, _y in zip(x, y):
    _x = _x % m
    if _x < 0:
      _x += m
    _y = _y % m
    if _y < 0:
      _y += m
    d += (_x - _y) ** 2
  return d

def modular_equals(x, y, m):
  for _x, _y in zip(x, y):
    _x = _x % m
    if _x < 0:
      _x += m
    _y = _y % m
    if _y < 0:
      _y += m
    if _x != _y:
      return False
  return True

class Chart():
  # We assume chart domains and images are balls.
  def __init__(self, domain_center, domain_radius, image_radius, map_, inverse_map, distance_function):
    self.distance_function = distance_function 
    self.domain_center = domain_center 
    self.image_center = map_(domain_center)
    self.domain_radius = domain_radius
    self.image_radius = image_radius
    self.map = map_
    self.inverse_map = inverse_map
    self.distance_function = distance_function

  def domain_contains(self, x):
    return self.distance_function(x, self.domain_center) < self.domain_radius

  def image_contains(self, x):
    return EuclideanManifold.distance_function(x, self.image_center) < self.image_radius

class Manifold(gymnasium.Env, Density, Geometry):
  def __init__(self, dim, ambient_dim):
    self.dim = dim
    self.ambient_dim = ambient_dim 
    self.max_step_size = 0.01 # TODO.
    self.observation_space = gymnasium.spaces.Box(low=-1.0, high=1.0, shape=[self.ambient_dim]) 
    self.action_space = gymnasium.spaces.Box(low=-1.0, high=1.0, shape=[self.dim])

  def reset(self, seed=None):
    self.state = self.starting_state()
    info = {}
    return self.state.copy(), info
  
  def step(self, action):
    # Warning: Undefined behavior if reset not called before this.
    self.state = self._manifold_step(self.state, action, self.max_step_size)
    reward = 0.0
    terminated = False
    truncated = False
    info = {}
    return self.state.copy(), reward, terminated, truncated, info

  def random_walk(self, n, starting_state=None, step_size=None):
    state = starting_state if starting_state is not None else self.starting_state() 
    samples = []
    for i in range(n):
      prob_state = self.pdf(state)
      accepted = False
      while not accepted:
        change_state = SphereManifold._sample_uniform(self.dim - 1)
        new_state = self._manifold_step(state, change_state, step_size if step_size is not None else self.max_step_size)
        prob_new_state = self.pdf(new_state)
        if np.random.uniform() < prob_new_state / prob_state:
          state = new_state 
          accepted = True
      samples.append(state)
    return np.array(samples)

  def _manifold_step(self, state, action, max_step_size):
    action_euclidean_size = np.linalg.norm(action)
    action_metric_size = self._metric_size(state, action) # This is a crude approximation.
    change_local_state = max_step_size * (action_euclidean_size / action_metric_size) * action
    # Search for a chart compatible with the step.
    for chart in self.charts:
      if chart.domain_contains(state):
        local_state = chart.map(state) 
        cand_local_state = local_state + change_local_state 
        if chart.image_contains(cand_local_state):
          return chart.inverse_map(cand_local_state)
    raise Exception("No compatible chart found.")

  def _metric_size(self, state, action):
    return np.matmul(action, np.matmul(self.metric_tensor(state), action.T)) 

  def starting_state(self):
    raise NotImplementedError

  def pdf(self, x):
    raise NotImplementedError

  def sample(self):
    raise NotImplementedError

  def distance_function(self, x, y):
    raise NotImplementedError

  def metric_tensor(self):
    raise NotImplementedError

  def implicit_function(self, c):
    raise NotImplementedError

class EuclideanManifold(Manifold):
  def __init__(self, dim, sampler):
    super(EuclideanManifold, self).__init__(dim, dim)
    self.low = -1.0 
    self.high = 1.0 
    self.sampler = sampler 

    self.charts = [
      Chart(
        domain_center=np.zeros(self.dim),
        domain_radius=np.inf,
        image_radius=np.inf,
        map_=lambda x: x,
        inverse_map=lambda x: x,
        distance_function=self.distance_function
      )
    ]

    if self.sampler['type'] == 'uniform':
      assert self.low <= self.sampler['low'] and self.sampler['high'] <= self.high

  def starting_state(self):
    return np.zeros(self.dim)

  def pdf(self, x):
    if self.sampler['type'] == 'uniform':
      if np.all(x >= self.sampler['low']) and np.all(x <= self.sampler['high']):
        return 1 / np.prod(self.sampler['high'] - self.sampler['low'])
      else:
        return 0.0
    elif self.sampler['type'] == 'gaussian':
      return np.exp(-np.sum((x - self.sampler['mean'])**2) / (2 * self.sampler['std']**2)) / (np.sqrt((2 * np.pi)**self.dim) * self.sampler['std'])

  def sample(self, n):
    if n > 1: # TODO.
      return np.array([self.sample(1) for _ in range(n)])
    if self.sampler['type'] == 'uniform':
      return np.random.uniform(self.sampler['low'], self.sampler['high'], self.dim)
    elif self.sampler['type'] == 'gaussian':
      return np.random.normal(self.sampler['mean'], self.sampler['std'], self.dim)

  @staticmethod
  def distance_function(x, y):
    return np.linalg.norm(x - y)

  def metric_tensor(self, x):
    return np.eye(self.dim)

  def implicit_function(self, c):
    if self.dim >= 3:
      raise ValueError
    else:
      return 0.0

class SphereManifold(Manifold):
  # We assume unit radius.
  def __init__(self, dim, sampler):
    assert dim == 2 # TODO.
    super(SphereManifold, self).__init__(dim, dim + 1)
    self.sampler = sampler

    # TODO. Right now this only works for dim=2 and has a singular point.
    self.charts = [
      Chart(
        domain_center=self._from_local(np.zeros(self.dim)),
        domain_radius=np.inf, # TODO
        image_radius=np.inf, # TODO
        map_=self._to_local,
        inverse_map=self._from_local,
        distance_function=self.distance_function
      )
    ]

  def starting_state(self):
    return self._from_local(np.zeros(self.dim))
    #return np.array([1.0] + [0.0] * self.dim)

  def pdf(self, x):
    if self.sampler['type'] == 'uniform':
      if np.linalg.norm(x) == 1: 
        return 1 / (2 * np.pi)**(self.dim / 2) 
      else:
        return 0.0
    elif self.sampler['type'] == 'vonmises_fisher':
      return scipy.stats.vonmises_fisher.pdf(x, self.sampler['mu'], self.sampler['kappa'])

  def sample(self, n):
    if n > 1: # TODO.
      return np.array([self.sample(1) for _ in range(n)])
    if self.sampler['type'] == 'uniform':
      return self._sample_uniform(self.dim)
    elif self.sampler['type'] == 'vonmises_fisher':
      return scipy.stats.vonmises_fisher.rvs(self.sampler['mu'], self.sampler['kappa'], size=1)[0]
      
  @staticmethod
  def distance_function(x, y):
    return np.arccos(np.dot(x, y))

  def metric_tensor(self, x):
    return np.array([
        [1.0, 0.0],
        [0.0, np.sin(x[0])**2]
      ])

  def _to_local(self, c): 
    theta = np.arccos(c[0])
    phi = np.arctan2(c[1], c[2])
    return np.array([theta, phi])

  def _from_local(self, c): 
    x = np.sin(c[0]) * np.cos(c[1])
    y = np.sin(c[0]) * np.sin(c[1])
    z = np.cos(c[0])
    return np.array([x, y, z])

  @staticmethod
  def _sample_uniform(dim):
    x = np.random.normal(0, 1, dim + 1)
    return x / np.linalg.norm(x)

  def implicit_function(self, c):
    return 1.0 - c[0]**2 - c[1]**2

class TorusManifold(Manifold):
  def __init__(self, dim):
    assert dim == 2 # TODO.
    super(TorusManifold, self).__init__(dim, dim + 1)

    self.r = 1/3 # Radius of "inner" sphere. 
    self.R = 2/3 # Radius of "outer" sphere.

    self.charts = [
      Chart(
        domain_center=self._from_local(np.zeros(self.dim)),
        domain_radius=np.inf, # TODO
        image_radius=np.inf, # TODO
        map_=self._to_local,
        inverse_map=self._from_local,
        distance_function=self.distance_function
      )
    ]

  def starting_state(self):
    local = np.zeros(self.dim) 
    return self._from_local(local)

  def pdf(self, x):
    # Uniform.
    if True: # TODO. Check if on surface.
      return 1 / ((2 * np.pi * self.r)**2 * self.R) # TODO. This is only valid for dim=2.

  def sample(self, n):
    if n > 1:
      return np.array([self.sample(1) for _ in range(n)])
    # TODO. This is wrong.
    local = np.random.uniform(-np.pi, np.pi, 2)
    return self._from_local(local)

  def distance_function(self, x, y):
    # Based on idea that cut toroidal is a cylinder... TODO. Could be wrong.
    x_local = self._to_local(x)
    y_local = self._to_local(y)

    theta_1 = standardize_angle(y_local[0] - x_local[0])
    theta_2 = standardize_angle(y_local[0] - x_local[0])
    theta = np.min([theta_1, theta_2])
    phi_1 = standardize_angle(y_local[1] - x_local[1])
    phi_2 = standardize_angle(y_local[1] - x_local[1])
    phi = np.min([phi_1, phi_2])

    theta_distance = theta * self.r
    phi_distance = phi * self.R 

    return np.sqrt(theta_distance**2 + phi_distance**2)

  def metric_tensor(self, x):
    return np.array([
      [(self.R + self.r * np.cos(x[1]))**2, 0],
      [0, self.r ** 2]
    ])

  def implicit_function(self, c):
    return np.sqrt(self.r**2 - (np.sqrt(c[0]**2 + c[1]**2) - self.R)**2)

  def _to_local(self, c):
    theta = np.arctan2(c[1], c[0])
    phi = np.arctan2(c[2], (np.sqrt(c[0]**2 + c[1]**2) - self.R) / self.r)
    return np.array([theta, phi])

  def _from_local(self, c):
    x = (self.R + self.r * np.cos(c[1])) * np.cos(c[0])
    y =  (self.R + self.r * np.cos(c[1])) * np.sin(c[0])
    z = self.r * np.sin(c[1])
    return np.array([x, y, z])

class HyperbolicParabolaManifold(Manifold):
  def __init__(self, dim):
    assert dim == 2 # TODO.
    super(HyperbolicParabolaManifold, self).__init__(dim, dim + 1)
    self.low = -1.0 
    self.high = 1.0 

  def pdf(self, x):
    raise NotImplementedError

  def sample(self, n):
    if n > 1:
      return np.array([self.sample(1) for _ in range(n)])
    u, v = np.random.uniform(self.low, self.high, 2)
    return self._from_local([u, v])

  def starting_state(self):
    return np.zeros(self.ambient_dim)

  def distance_function(self, x, y):
    raise NotImplementedError

  def metric_tensor(self, x):
    raise NotImplementedError

  def impicit_function(self, c):
    return c[0]**2 - c[1]**2

  def _to_local(self, c):
    u = c[0]
    v = c[1]
    return np.array([u, v])

  def _from_local(self, c):
    x = c[0]
    y = c[1]
    z = c[0] * c[1]
    return np.array([x, y, z])

class HyperboloidManifold(Manifold):
  def __init__(self, dim):
    assert dim == 2 # TODO.
    super(HyperboloidManifold, self).__init__(dim, dim + 1)
    self.a = 2**-0.5
    self.c = 1.0

  def pdf(self, x):
    raise NotImplementedError

  def sample(self, n):
    if n > 1:
      return np.array([self.sample(1) for _ in range(n)])
    u = np.random.uniform(-1.0, 1.0)
    v = np.random.uniform(-np.pi, np.pi)
    return self._from_local([u, v])

  def starting_state(self):
    return np.zeros(self.ambient_dim)

  def distance_function(self, x, y):
    raise NotImplementedError

  def metric_tensor(self, x):
    raise NotImplementedError

  def implicit_function(self):
    return self.c[0]**2 + self.c[1]**2

  def _to_local(self, c):
    raise NotImplementedError

  def _from_local(self, c):
    x = self.a * np.sqrt(1 + c[0]**2) * np.cos(c[1])
    y = self.a * np.sqrt(1 + c[0]**2) * np.sin(c[1])
    z = self.c * c[0]
    return np.array([x, y, z])