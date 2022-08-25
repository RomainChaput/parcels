from os import path, system
from glob import glob
import numpy as np
import pytest
import sys
import xarray as xr
try:
    from mpi4py import MPI
except:
    MPI = None


@pytest.mark.skipif(sys.platform.startswith("darwin"), reason="skipping macOS test as problem with file in pytest")
@pytest.mark.parametrize('pset_mode', ['soa', 'aos'])
@pytest.mark.parametrize('repeatdt, maxage', [(20*86400, 600*86400), (10*86400, 10*86400)])
@pytest.mark.parametrize('nump', [4, 8])
def test_mpi_run(pset_mode, tmpdir, repeatdt, maxage, nump):
    if MPI:
        stommel_file = path.join(path.dirname(__file__), '..', 'parcels',
                                 'examples', 'example_stommel.py')
        outputMPI = tmpdir.join('StommelMPI.zarr')
        outputNoMPI = tmpdir.join('StommelNoMPI.zarr')

        system('mpirun -np 2 python %s -p %d -o %s -r %d -a %d -psm %s' % (stommel_file, nump, outputMPI, repeatdt, maxage, pset_mode))
        system('python %s -p %d -o %s -r %d -a %d -psm %s' % (stommel_file, nump, outputNoMPI, repeatdt, maxage, pset_mode))

        files = glob(path.join(outputMPI, "proc*"))
        ds11 = xr.open_zarr(files[0])
        ds12 = xr.open_zarr(files[1])
        ds11 = ds11.assign_coords({'traj': ('traj', ds11.trajectory.values)})
        ds12 = ds12.assign_coords({'traj': ('traj', ds12.trajectory.values)})
        ds1 = xr.merge([ds11, ds12], compat='no_conflicts')

        ds2 = xr.open_zarr(outputNoMPI)

        for v in ds2.variables.keys():
            if v == 'time':
                continue  # skip because np.allclose does not work well on np.datetime64
            assert np.allclose(ds1.variables[v][:], ds2.variables[v][:], equal_nan=True)

        for a in ds2.attrs:
            if a != 'parcels_version':
                assert ds1.attrs[a] == ds2.attrs[a]

        ds1.close()
        ds2.close()
