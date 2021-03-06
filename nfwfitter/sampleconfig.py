import readMXXL
simreader = readMXXL.MXXLSimReader()

import nfwfit
model = nfwfit.NFW_MC_Model()
massprior='linear'

import colossusMassCon
massconRelation = colossusMassCon.ColossusMC()
colossusmcname='diemer15'

import nfwfit
fitter = nfwfit.PDFScanner()

import rescalecluster
rescalecluster = rescalecluster.RedshiftRescaler()
targetz=0.9

import galaxypicker
densitypicker = galaxypicker.DensityPicker()
nperarcmin=50.


import galaxypicker
fovpicker = galaxypicker.SquareMosaic()


import simutils
galaxypicker = simutils.Composite(densitypicker,fovpicker)

import betacalcer
betacalcer = betacalcer.FixedBeta()
beta = 0.3


import shearnoiser
shearnoiser = shearnoiser.GaussianShapeNoise()
shapenoise = 0.02

import centergenerator
centergenerator = centergenerator.SZAnalytic()
szbeam=1.3
coresize=1.25
sz_xi=8.1


import basicBinning
binner = basicBinning.GaussianFixedBins()
profileMax = 1.5
profileMin = 0.5
binspacing = 'linear'
nbins = 12
profilecol = 'r_mpc'


import binnoiser
binnoiser = binnoiser.NoBinNoise()

import profilebuilder
profilebuilder = profilebuilder.ProfileBuilder()

