######################
# Reads in BK11 files so that nfwfit.py can use them
######################

import astropy.io.fits as pyfits, ldac
import nfwutils
import numpy as np

class BK11SimReader(object):

    def __init__(self, config):

        self.config = config


    def getCosmology(self):
        return nfwutils.Cosmology(omega_m = 0.27, omega_l = 0.73, h = 0.7)

    def effectiveBeta(self):

        if 'beta' in self.config:
            return self.config.beta
        return None

    def load(self, filebase):

        return BK11Sim(filebase, self.effectiveBeta())


class BK11Sim(object):

    def __init__(self, filename, effectiveBeta):


        sim = ldac.LDACCat(pyfits.open(filename)[1])

        boxlength = sim['BOXWIDTHCOMOVINGHINVMPC'] / nfwutils.global_cosmology.h
        gridsize = np.sqrt(float(sim['A00'].shape[1]))

        clusterz = float(sim['ZLENS'])
        self.zcluster = clusterz

        ####becker angles

        Ng = 512

        dc_readout = nfwutils.global_cosmology.comovingdist(clusterz)+sim['BOXLENGTHCOMOVINGHINVMPC'][0]/(2.0*nfwutils.global_cosmology.h)
        da = np.arctan2(sim['BOXWIDTHCOMOVINGHINVMPC'][0]/nfwutils.global_cosmology.h,dc_readout)/np.pi*180.0*60.0/Ng

        xcen = Ng/2.0
        ycen = Ng/2.0

        radii_arcmin = np.zeros((Ng, Ng))
        cosphi = np.zeros((Ng,Ng))
        sinphi = np.zeros((Ng,Ng))
        x_arcmin = np.zeros((Ng,Ng))
        y_arcmin = np.zeros((Ng,Ng))

        for i in range(Ng):
            for j in range(Ng):
                xr = (i + 0.5 - xcen)*da
                yr = (j + 0.5 - ycen)*da
                r = np.sqrt(xr*xr + yr*yr)
                radii_arcmin[i,j] = r
                x_arcmin[i,j] = xr
                y_arcmin[i,j] = yr

                cosphi[i,j] = xr/r
                sinphi[i,j] = yr/r


        A00 = sim['A00'][0]
        A11 = sim['A11'][0]
        A10 = sim['A10'][0]
        A01 = sim['A01'][0]

        kappa = 0.5*(2- A00 - A11)
        gamma1 = 0.5*(A11 - A00)
        gamma2 = -0.5*(A01+A10)

        self.redshifts = np.ones(len(self.r_mpc))*float(sim['ZSOURCE'])
        simBeta_s = nfwutils.global_cosmology.beta_s(self.redshifts, clusterz)

        if effectiveBeta is None:
            self.beta_s = simBeta_s
        else:
            self.beta_s = (effectiveBeta / nfwutils.global_cosmology.beta([1e6], self.zcluster))*np.ones_like(self.redshifts)

        betaratio = self.beta_s / simBeta_s


        self.g1 = (betaratio*gamma1/(1-betaratio*kappa)).flatten()
        self.g2 = (betaratio*gamma2/(1-betaratio*kappa)).flatten()

        self.x_arcmin = x_arcmin.flatten()
        self.y_arcmin = y_arcmin.flatten()

        self.r_arcmin = radii_arcmin.flatten()
        self.r_mpc = (self.r_arcmin/60.)*(np.pi/180.)*nfwutils.global_cosmology.angulardist(clusterz)

        cosphi = cosphi.flatten()
        sinphi = sinphi.flatten()
        self.sin2phi = 2.0*sinphi*cosphi
        self.cos2phi = 2.0*cosphi*cosphi-1.0



        self.m500 = sim['M500C']
        self.m200 = sim['M200C']
        self.c200 = sim['C200C']

