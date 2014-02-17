#!/usr/bin/env python
############################

import glob, cPickle, sys, os, re
import numpy as np
import nfwutils, nfwfit

###########################

simtype=sys.argv[1]
outdir=sys.argv[2]

idpatterns = dict(mxxl = re.compile('halo_cid(\d+)\.out'),
                  bcc = re.compile('cluster_(\d+)\.out'),
                  bk11snap141 = re.compile('haloid(\d+)_zLens.+'),
                  bk11snap124 = re.compile('haloid(\d+)_zLens.+'))

idpattern = idpatterns[simtype]

answers = cPickle.load(open('{0}_answers.pkl'.format(simtype), 'rb'))

outputfiles = glob.glob('%s/*.out' % outdir)
nhalos = len(outputfiles)

ids = np.zeros(nhalos)
measured_m200s = np.zeros(nhalos)
measured_m500s = np.zeros(nhalos)
measured_cs = np.zeros(nhalos)
measured_rs = np.zeros(nhalos)

true_m200s = np.zeros(nhalos)
true_m500s = np.zeros(nhalos)
true_cs = np.zeros(nhalos)
redshifts = np.zeros(nhalos)

results = dict(ids = ids,
                    measured_m200s = measured_m200s, 
                    measured_m500s = measured_m500s,
                    measured_cs = measured_cs,
                    measured_rs = measured_rs,
                    true_m200s = true_m200s,
                    true_m500s = true_m500s,
                    true_cs = true_cs,
                    redshifts = redshifts)

class WeirdException(Exception): pass 


#load up the environment for cosmology, and mc relation if used
config = nfwfit.readConfiguration('{0}/config.sh'.format(outdir))
simreader = nfwfit.buildSimReader(config)
nfwutils.global_cosmology.set_cosmology(simreader.getCosmology())
fitter = nfwfit.buildFitter(config)



for i,output in enumerate(outputfiles):

    filebase = os.path.basename(output)
        
    match = idpattern.match(filebase)

    haloid = int(match.group(1))

    try:
        truth = answers[haloid]
    except KeyError:
        print 'Failure at {0}'.format(output)
        raise

    true_m200s[i] = truth['m200']
    true_m500s[i] = truth['m500']
    true_cs[i] = truth['concen']
    redshifts[i] = truth['redshift']



    input = open(output)
    measured, nfails = cPickle.load(input)
    input.close()


    if measured is None:
        print 'All failed in {0}'.format(output)
        continue


    measured_m200s[i] = measured['m200']*fitter.model.massScale*nfwutils.global_cosmology.h
    if 'c200' in measured:
        measured_cs[i] = measured['c200']
    else:
        ## need to dig up the mc relation
        measured_cs[i] = fitter.model.massconRelation(measured_m200s[i], 
                                                      redshifts[i], 
                                                      fitter.model.overdensity)

    #####
    #calculate m500

    measured_rs[i] = nfwutils.rscaleConstM(measured_m200s[i], measured_cs[i],redshifts[i],
                                  fitter.model.overdensity)
    measured_m500s[i] = nfwutils.Mdelta(measured_rs[i],
                                        measured_cs[i],
                                        redshifts[i],
                                        500)







cPickle.dump(results, open('%s/consolidated.pkl' % outdir, 'w'))

    
    
