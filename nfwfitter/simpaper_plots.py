##############
# Plots for the sims paper
#############

import copy
import pylab
import numpy as np
import cPickle


# import nfwnoise
import nfwutils
import nfwfit
import varcontainer
#import publication_plots as pp
import basicMassCon
import deconvolvedlognorm
import pymc
#import fitmodel
import confidenceinterval as ci
import plotsimdistros as psd
import simutils
import load_chains
import readtxtfile

#####

#outputdir = '/Users/dapple/astro/mxxlsims/output'
outputdir= '/project/kicp/avestruz/storage/'
#####


################
## Statistics & Noise Section
################


def likelihoodPlots():
    '''Show the lensing likelihoods, to make the point that yes, they are almost symetric in linear space, but Gaussian approximations are poor.'''

    linfig = pylab.figure()
    linax = linfig.add_subplot(1,1,1)

    logfig = pylab.figure()
    logax = logfig.add_subplot(1,1,1)

    figs = [linfig, logfig]

    true_masses = [2e14, 1e15]
    linestyles = ['-', '--']

    for true_mass, linestyle in zip(true_masses, linestyles):

        m200s = np.arange(-5.05e14, 3e15, 1e13)
        r_mpc_edges = np.linspace(0.75, 3., 13)
        r_mpc = (r_mpc_edges[1:] + r_mpc_edges[:-1])/2.
        zcluster = 0.415 #median of megacam

        duffy = basicMassCon.Duffy()
        c_duff = duffy(true_mass * nfwutils.global_cosmology.h, zcluster, 200.)



        beta_s = 0.49 #median of megacam

        g_truth = nfwnoise.createPerfectProfile(true_mass, c_duff, zcluster, r_mpc, beta_s)

        ngalsperarcmin = 9.7 #median of megacam set
        r_arcmin_edges = (r_mpc_edges/nfwutils.global_cosmology.angulardist(zcluster))*(180./np.pi)*60
        bin_areas = np.pi*(r_arcmin_edges[1:]**2 - r_arcmin_edges[:-1]**2)
        ngals_per_bin = ngalsperarcmin * bin_areas
        g_err = 0.25 / np.sqrt(ngals_per_bin)





        #calcualte pdf for duffy

        config = {}
        config['model'] = nfwfit.NFW_MC_Model()
        config['massconRelation'] = basicMassCon.Duffy()
        simutils.runConfigure(config)


        likelihood = nfwnoise.Likelihood(config)
        likelihood.bindData(r_mpc, g_truth, g_err, beta_s, zcluster)



        duffy_logpdf = np.array([likelihood(m200) for m200 in m200s])
        duffy_pdf = np.exp(duffy_logpdf - np.max(duffy_logpdf))
        duffy_pdf = duffy_pdf / np.trapz(duffy_pdf, m200s)


        #plot


        linax.plot(m200s, duffy_pdf, 
                   marker='None', linestyle=linestyle, 
                   color = 'k',
                   linewidth = 2., 
                   label='$M_{200} = $%1.1f x $10^{14} M_{\odot}$' % (true_mass / 1e14))

        linax.axvline(true_mass, c=(0.6, 0.6, 0.6), linewidth=2, linestyle=linestyle)


        posmass = m200s > 0
        log10m200s = np.log10(m200s[posmass])
        log10pdf = duffy_pdf[posmass]
        log10pdf = log10pdf / np.trapz(log10pdf, log10m200s)
        logax.plot(log10m200s, log10pdf, 
                   marker='None', linestyle=linestyle, 
                   color = 'k',
                   linewidth = 2., 
                   label='$M_{200} = $%1.1f x $10^{14} M_{\odot}$' % (true_mass / 1e14))

        logax.axvline(np.log10(true_mass), c=(0.6, 0.6, 0.6), linewidth=2, linestyle=linestyle)



    linax.legend()
    linax.set_xlabel(r'$M_{200} [M_{\odot}]$', fontsize=18)
    linax.set_ylabel(r'Likelihood($M_{200}$)', fontsize=18)
    linax.set_xlim(-0.5e15, 2.5e15)

    linfig.tight_layout()

    linfig.savefig('docs/figures/likelihood_shape.png')
    linfig.savefig('docs/figures/likelihood_shape.eps')
    linfig.savefig('docs/figures/likelihood_shape.pdf')


    logax.legend(loc='upper left')
    logax.set_xlabel(r'$\mathrm{log}_{10}M_{200}$', fontsize=18)
    logax.set_ylabel(r'Likelihood($\mathrm{log}_{10}M_{200}$)', fontsize=18)
    logax.set_xlim(np.log10(np.min(m200s[posmass])), np.log10(2.5e15))
    logfig.tight_layout()
    logfig.savefig('docs/figures/likelihood_logshape.png')
    logfig.savefig('docs/figures/likelihood_logshape.eps')
    logfig.savefig('docs/figures/likelihood_logshape.pdf')

    return figs

##############
    

def calcMaxlikeDistro(outputfile = 'maxlikedistro_paperplot_lowsn.pkl', ngalsperarcmin=5):
    '''show that using maximum likelihood estimators does not recover truth'''

    

    figs = []

    #megacamstyle

    ntrials = 2000
    samplesize = 25

    r_mpc_edges = np.linspace(0.75, 3., 13)
    r_mpc = (r_mpc_edges[1:] + r_mpc_edges[:-1])/2.
    zcluster = 0.3 
    duffy = basicMassCon.Duffy(None)
    c200 = 4.0
    beta_s = nfwutils.global_cosmology.beta_s([1.0], zcluster)[0]

    r_arcmin_edges = (r_mpc_edges/nfwutils.global_cosmology.angulardist(zcluster))*(180./np.pi)*60
    bin_areas = np.pi*(r_arcmin_edges[1:]**2 - r_arcmin_edges[:-1]**2)
    ngals_per_bin = ngalsperarcmin * bin_areas
    g_err = 0.25 / np.sqrt(ngals_per_bin)

    m200s = np.arange(1e12, 5e15, 1e13)
    
    config = varcontainer.VarContainer()
    config.massconmodule = 'basicMassCon'
    config.massconrelation = 'constant'
    config.concentration = c200
    model = nfwfit.buildModel(config)
    likelihood = nfwnoise.Likelihood(config)


    unweightedbootstraps_mean = np.zeros(ntrials)
    weightedaverages = np.zeros(ntrials)
    wlssaverage = np.zeros(ntrials)
    linear_fit = np.zeros(ntrials)
    smithaverages = np.zeros(ntrials)
    pdfaverages = np.zeros(ntrials)

    for curtrial in range(ntrials):
        
        true_masses = 10**np.random.uniform(np.log10(5e14), np.log10(2e15), samplesize)
        lens_masses = true_masses * np.exp(0.2*np.random.standard_normal(size=samplesize))

        #compute individual cluster likelihoods
        maxlike_masses = np.zeros(samplesize)
        maxlike_errs = np.zeros((2,samplesize))
        pdfs = np.zeros((samplesize, len(m200s)))
        logpdf = np.zeros(len(m200s))
    
        for curcluster in range(samplesize):
        
            g_obs = nfwnoise.createPerfectProfile(lens_masses[curcluster], c200, 
                                                  zcluster, r_mpc, beta_s) + \
                g_err*np.random.standard_normal(size=len(g_err))

            fitter = nfwfit.NFWFitter(None, model, config)

            maxlikemass, maxlikeerr = fitter.minChisqMethod(r_mpc, g_obs, g_err,
                                                            beta_s, beta_s**2, zcluster,
                                                            guess = [true_masses[curcluster]/model.massScale])

            maxlike_masses[curcluster] = maxlikemass['m200']
            try:
                maxlike_errs[:,curcluster] = maxlikeerr['m200']
            except TypeError:
                maxlike_errs[:,curcluster] = (maxlikeerr['m200'], maxlikeerr['m200'])

            likelihood.bindData(r_mpc, g_obs, g_err, beta_s, zcluster)

            for i, m200 in enumerate(m200s):
                logpdf[i] = likelihood(m200)
            pdf = np.exp(logpdf - np.max(logpdf))
            pdf /= np.trapz(pdf, m200s)
            pdfs[curcluster,:] = pdf

        maxlike_masses *= model.massScale
        maxlike_errs = np.abs(maxlike_errs*model.massScale)

        maxlike_logratio = np.log(maxlike_masses / true_masses)




        #combine using different formulisms
        bootstraps = np.zeros(1000)

        for curboot in range(1000):
            booted = np.random.randint(0, samplesize, samplesize)
            bootstraps[curboot] = np.mean(maxlike_logratio[booted])


        unweightedbootstraps_mean[curtrial] = np.mean(bootstraps)



        maxlike_simpleerr = np.sum(maxlike_errs, axis=0)/(2.*maxlike_masses)

        weight = 1./maxlike_simpleerr**2
        weightedaverages[curtrial] = np.sum(weight*maxlike_logratio)/np.sum(weight)
        
        wlssaverage_weights = 1./(maxlike_simpleerr**2 + (0.2*maxlike_masses)**2)
        wlssaverage[curtrial] = np.sum(wlssaverage_weights*maxlike_logratio)/np.sum(wlssaverage_weights)
        
            
        smithweight = 1./(np.sum(maxlike_errs, axis=0)/2.)**2
        smithaverages[curtrial] = np.sum(smithweight*maxlike_logratio)/np.sum(smithweight)

        
        
        halos = [dict(id=curcluster,
                      true_mass = true_masses[curcluster],
                      masses = m200s,
                      pdf = pdfs[curcluster,:]) for curcluster in range(samplesize)]

        
        pdfmodel = deconvolvedlognorm.buildPDFModel(halos)
        pdfmap = pymc.MAP(pdfmodel)
        pdfmap.fit()
        pdfaverages[curtrial] = pdfmap.logmu.value

        

        linefitter = fitmodel.FitModel(true_masses/1e14, maxlike_masses/1e14,
                                       np.sum(maxlike_errs/1e14,axis=0)/2.,
                                       fitmodel.RatioModel, guess = [1.])
        linefitter.fit()
        linear_fit[curtrial] = linefitter.par_vals['a0']




        

    results = dict(unweightedbootstrapsmean = np.exp(unweightedbootstraps_mean),
                   weightedaverages         = np.exp(weightedaverages),
                   wlssaverage              = np.exp(wlssaverage),
                   smithaverages            = np.exp(smithaverages),
                   pdfaverages              = np.exp(pdfaverages),
                   linearfit                = linear_fit
               )

    with open(outputfile, 'wb') as output:
        cPickle.dump(results, output, -1)


###################

def bootstrapdistro(distro, foo = np.mean, nboots=1000):

    booted = np.zeros(nboots)
    for i in range(nboots):
        booted[i] = foo(distro[np.random.randint(0, len(distro), len(distro))])

    return np.mean(booted), np.std(booted)

def maxlikeComparePlots(inputfile = 'maxlikedistro_paperplot_highsn_large.pkl', outputbase = 'maxlike_comparison'):

    with open(inputfile, 'rb') as input:
        distros = cPickle.load(input)

    fig = pylab.figure()
    ax = fig.add_subplot(1,1,1)

    labels = [('unweightedbootstrapsmean',  'Bootstrap Geometric Mean', '^', 'r'),
              ('weightedaverages',          'Weighted Geometric Mean', 's', 'r'),
              ('wlssaverage',               'Weighted+LSS Geometric Mean', 'p', 'r'),
              ('smithaverages',             'Absolute Err Geometric Mean', 'd', 'r'),
              ('linearfit',                 'Maxlike Linear Fit', 'v', 'k'),
              ('pdfaverages',               'PDF w/intrinsic scatter', 'o', 'k')]

    for key, label, marker, color in labels:
        
        bias, biaserr = bootstrapdistro(distros[key])
        stdev, stdeverr = bootstrapdistro(distros[key], np.std)

        ax.errorbar(bias, stdev, stdeverr, biaserr, label=label, marker=marker, color=color, linestyle='none', markersize=10)


    linearfit_bias = [bootstrapdistro(distros['linearfit'])[0]]
    linearfit_precision = [bootstrapdistro(distros['linearfit'], np.std)[0]]
    for inputfile in 'maxlikedistro_paperplot_lowsn.pkl maxlikedistro_paperplot_extralowsn.pkl'.split():
        with open(inputfile, 'rb') as input:
            distros = cPickle.load(input)
        linearfit_bias.append(bootstrapdistro(distros['linearfit'])[0])
        linearfit_precision.append(bootstrapdistro(distros['linearfit'], np.std)[0])
        

    ax.plot(np.array(linearfit_bias), linearfit_precision, 'k--')
    ax.axvline(1.0, c='k', linestyle=':')
    ax.set_xlim(0.8, 1.1)
    ax.set_ylim(0.0, 0.15)
    ax.set_xscale('log')
    ax.set_xticks([0.8, 0.9, 1.0, 1.1])
    ax.set_xticklabels('0.8 0.9 1.0 1.1'.split())
    ax.set_xlabel('Bias [Lensing / True]', fontsize=18)
    ax.set_ylabel('Precision', fontsize=18)
    ax.legend(numpoints=1, ncol=1, loc='lower left', frameon=False)


        
    

    fig.tight_layout()

    fig.savefig('figures/{}.png'.format(outputbase))
    fig.savefig('figures/{}.eps'.format(outputbase))
    fig.savefig('figures/{}.pdf'.format(outputbase))



    return fig

    
############################

def compareNoiseProfiles(data = None):
    ''' Compare intrinsic noise levels to assumed shape noise'''

    if data is None:
        data = {}

    if 'centers_mpc' not in data:

        config = nfwfit.readConfiguration('/vol/euclid1/euclid1_1/dapple/mxxl_lensing/mxxlsnap54/general-c4-r10-n0_0-xrayNONE/config.sh')

        simreader = nfwfit.buildSimReader(config)

        nfwutils.global_cosmology.set_cosmology(simreader.getCosmology())

        fitter = nfwfit.buildFitter(config)

        intrnoise_profiles = []

        for haloid in range(800, 880):

            catbase = '/vol/euclid1/euclid1_raid1/dapple/mxxl_lensing/mxxlsnap54/halo_54_{}_0'.format(haloid)

            catalog = nfwfit.readSimCatalog(catbase, simreader, config)

            r_mpc, ghat, sigma_ghat, beta_s, beta_s2, zlens = fitter.prepData(catalog)

            intrnoise_profiles.append(sigma_ghat)

        intrnoise_profiles = np.row_stack(intrnoise_profiles)
        intrnoise = np.mean(intrnoise_profiles, axis=0)
        intrnoise_err = np.std(intrnoise_profiles, axis=0)

        edges_mpc = np.linspace(config.profilemin, config.profilemax, config.nbins+1)
        centers_mpc = (edges_mpc[1:] + edges_mpc[:-1])/2.
        dL = nfwutils.global_cosmology.angulardist(zlens)
        edges_arcmin = (edges_mpc/dL)*(180/np.pi)*60
        bin_areas = np.pi*(edges_arcmin[1:]**2 - edges_arcmin[:-1]**2)

        shapesigma = 0.25
        galdensity = 20. # per sq arc min
        shape_noise = shapesigma / np.sqrt(galdensity*bin_areas)

        data['centers_mpc'] = centers_mpc
        data['intrnoise'] = intrnoise
        data['intrnoise_err'] = intrnoise_err
        data['shape_noise'] = shape_noise

    else:

        centers_mpc = data['centers_mpc']
        intrnoise = data['intrnoise']
        intrnoise_err = data['intrnoise_err']
        shape_noise = data['shape_noise']
    

    fig = pylab.figure()
    ax = pylab.gca()

    ax.plot(centers_mpc, intrnoise/intrnoise[2], label='Intrinsic Noise [80 cluster avg]', marker='None', linestyle='-', linewidth = 2, color = pp.colors[0])
    ax.plot(centers_mpc, shape_noise/shape_noise[2], marker='None', linestyle='-', linewidth = 3, color = pp.colors[1], label='Shape Noise')
    
    ax.legend(loc='upper right')
    ax.set_xlabel('Radius [Mpc]', fontsize=16)
    ax.set_ylabel('Relative Shear Error [Arbit Norm]', fontsize=16)

    fig.tight_layout()

    fig.savefig('figures/relative_shear_noise.png')
    fig.savefig('figures/relative_shear_noise.pdf')
    fig.savefig('figures/relative_shear_noise.eps')


    return fig, data

###########################
## Simulation results based on changing obs setup
#############

def compareSimPlot(outputname, chaindirs, labels, xoffsets, deltas = [500, 200], metalabel = None):
    '''Refactored plot code'''

    for delta in deltas:

        meansfig = pylab.figure()
        meansax = meansfig.add_subplot(1,1,1)
        
        stdsfig = pylab.figure()
        stdax = stdsfig.add_subplot(1,1,1)

        patches = []

        for curentry, chaindir in enumerate(chaindirs):
            
            patch, summary = psd.precomputedLogNormDistro(chaindir, 
                                                          delta,
                                                          meansax,
                                                          stdax,
                                                          colorindex = curentry,
                                                          biaslabel = False,
                                                          alpha = 1.0,
                                                          xoffset = xoffsets[curentry])


            patches.append(patch)




        
        
        meansax.set_xscale('log')
        meansax.set_xlabel(r'Mass $M_{%d} [10^{14} M_{\odot}]$' % delta, fontsize=16)
        meansax.set_ylabel(r'Mean Bias in $Ln(M_{%d})$' % delta, fontsize=16)
        meansax.axhline(1.0, c='k', linewidth=3, linestyle='--')
        meansax.set_xlim(1e14, 5e15)
        # meansax.set_ylim(0.5, 1.3)
        meansax.set_xticks([1e15])
        meansax.set_xticklabels(['10'])
        meansax.set_xticks([3e14, 4e14, 5e14, 6e14, 7e14, 8e14, 9e14, 2e15, 3e15, 4e15], minor=True)
        meansax.set_xticklabels(['', '4', '', '6', '', '8', '', '20', '', '40'], minor=True)
        meansax.legend(patches[::-1], labels[::-1], loc='lower left')

        if metalabel is not None:
            meansax.text(2e15, 1.2, metalabel)
        
        meansfig.canvas.draw()
        meansfig.tight_layout()
        filebase = 'docs/figures/{}_bias.delta{}'.format(outputname, delta)
        meansfig.savefig('{}.png'.format(filebase))
        meansfig.savefig('{}.pdf'.format(filebase))
        meansfig.savefig('{}.ps'.format(filebase))
        meansfig.savefig('{}.eps'.format(filebase))
        
        stdax.set_xscale('log')
        stdax.set_xlabel(r'Mass $M_{%d} [10^{14} M_{\odot}]$' % delta, fontsize=16)
        stdax.set_ylabel(r'Noise Magnitude $\sigma$', fontsize=16)
        stdax.set_xlim(1e14, 5e15)
        stdax.set_ylim(0.0, 0.6)
        stdax.set_xticks([1e15])
        stdax.set_xticklabels(['10'])
        stdax.set_xticks([3e14, 4e14, 5e14, 6e14, 7e14, 8e14, 9e14, 2e15, 3e15, 4e15], minor=True)
        stdax.set_xticklabels(['', '4', '', '6', '', '8', '', '20', '', '40'], minor=True)
        stdax.legend(patches[::-1], labels[::-1], loc='upper left')

        if metalabel is not None:
            stdax.text(2e15, 1.2, metalabel)

        stdsfig.canvas.draw()
        stdsfig.tight_layout()
        filebase = 'docs/figures/{}_sigma.delta{}'.format(outputname, delta)
        stdsfig.savefig('{}.png'.format(filebase))
        stdsfig.savefig('{}.pdf'.format(filebase))
        stdsfig.savefig('{}.ps'.format(filebase))
        stdsfig.savefig('{}.eps'.format(filebase))


##########

markers = ['o', '^', 's']

def compare2DimSimPlot(outputname, chaindirs, labels, xoffsets, deltas = [500, 200], biasylim = (0.5, 1.3)):
    '''Refactored plot code ---> Too many things in here'''

    for delta in deltas:

        meansfig = pylab.figure()
        meansax = meansfig.add_subplot(1,1,1)
        
        stdsfig = pylab.figure()
        stdax = stdsfig.add_subplot(1,1,1)

        majorpatches = []
        minorpatches = []

        for curmajor, chaindirset in enumerate(chaindirs):



            for curminor, chaindir in enumerate(chaindirset):

                alpha = 1.0
                suppressXerr = False
                if curminor > 0:
                    alpha = 0.5



                patch, summary = psd.precomputedLogNormDistro(chaindir, 
                                                              delta,
                                                              meansax,
                                                              stdax,
                                                              colorindex = curmajor,
                                                              biaslabel = False,
                                                              marker = markers[curminor],
                                                              alpha = alpha,
                                                              xoffset = xoffsets[curmajor],
                                                              suppressXerr = suppressXerr,
                                                              patchAsRect = False)


                if curmajor == 0:
                    patchcopy = copy.copy(patch)
                    patchcopy.set_markerfacecolor('k')
                    minorpatches.append(patchcopy)

                if curminor == 0:
                    majorpatches.append(patch)




        allpatches = majorpatches + minorpatches
        alllabels = labels[0] + labels[1]
        
        
        meansax.set_xscale('log')
        meansax.set_xlabel(r'Mass $M_{%d} [10^{14} M_{\odot}]$' % delta, fontsize=16)
        meansax.set_ylabel(r'Mean Bias in $Ln(M_{%d})$' % delta, fontsize=16)
        meansax.axhline(1.0, c='k', linewidth=3, linestyle='--')
        meansax.set_xlim(1e14, 5e15)
        meansax.set_ylim(*biasylim)
        meansax.set_xticks([1e15])
        meansax.set_xticklabels(['10'])
        meansax.set_xticks([3e14, 4e14, 5e14, 6e14, 7e14, 8e14, 9e14, 2e15, 3e15, 4e15], minor=True)
        meansax.set_xticklabels(['', '4', '', '6', '', '8', '', '20', '', '40'], minor=True)
        meansax.legend(allpatches[::-1], alllabels[::-1], loc='lower left', numpoints=1, ncol=2)
        meansfig.canvas.draw()
        meansfig.tight_layout()
        filebase = 'docs/figures/{}_bias.delta{}'.format(outputname, delta)
        meansfig.savefig('{}.png'.format(filebase))
        meansfig.savefig('{}.pdf'.format(filebase))
        meansfig.savefig('{}.ps'.format(filebase))
        meansfig.savefig('{}.eps'.format(filebase))
        
        stdax.set_xscale('log')
        stdax.set_xlabel(r'Mass $M_{%d} [10^{14} M_{\odot}]$' % delta, fontsize=16)
        stdax.set_ylabel(r'Noise Magnitude $\sigma$', fontsize=16)
        stdax.set_xlim(1e14, 5e15)
        stdax.set_ylim(0.0, 0.6)
        stdax.set_xticks([1e15])
        stdax.set_xticklabels(['10'])
        stdax.set_xticks([3e14, 4e14, 5e14, 6e14, 7e14, 8e14, 9e14, 2e15, 3e15, 4e15], minor=True)
        stdax.set_xticklabels(['', '4', '', '6', '', '8', '', '20', '', '40'], minor=True)
        stdax.legend(allpatches[::-1], alllabels[::-1], loc='lower left', numpoints=1, ncol=2)
        stdsfig.canvas.draw()
        stdsfig.tight_layout()
        filebase = 'docs/figures/{}_sigma.delta{}'.format(outputname, delta)
        stdsfig.savefig('{}.png'.format(filebase))
        stdsfig.savefig('{}.pdf'.format(filebase))
        stdsfig.savefig('{}.ps'.format(filebase))
        stdsfig.savefig('{}.eps'.format(filebase))


##########


def compareInnerFitRadius():
    '''Compare bias levels when MC and centering as good as can be, for varying inner radial fit limits'''

    mxxlsnap=54

    configtemplate = 'general-diemer15-r{}-xrayNONE-n2_4-nov2016'
    radialranges = [19, 3, 6, 9]
    configs = [configtemplate.format(r) for r in radialranges]

    chaindirs = ['/users/dapple/euclid1_2/rundlns/mxxlsnap{}/{}'.format(mxxlsnap, config) for config in configs]
    

    labels = ['100kpc', '250kpc', '500kpc', '750kpc']

    xoffsets = [0.97, 0.99, 1.01, 1.03]

    outputname = 'compare_nfw_innerfitrange'

    compareSimPlot(outputname, chaindirs, labels, xoffsets)


    ##########

def compareOuterFitRadius():
    '''Compare bias levels when MC and centering as good as can be, for varying outer radial fit limits'''

    mxxlsnap=54

    configtemplate = 'general-diemer15-r{}-xrayNONE-n2_4-nov2016'
    radialranges = [5, 20, 6, 7]
    configs = [configtemplate.format(r) for r in radialranges]

    chaindirs = ['/users/dapple/euclid1_2/rundlns/mxxlsnap{}/{}'.format(mxxlsnap, config) for config in configs]
    

    labels = ['1.5 Mpc', '2.0 Mpc', '2.5 Mpc', '3.0 Mpc']

    xoffsets = [0.97, 0.99, 1.01, 1.03]

    outputname = 'compare_nfw_outerfitrange'

    compareSimPlot(outputname, chaindirs, labels, xoffsets)


    ##########

def compareMCRelation_RadialRange():
    '''Compare bias levels using different MC relations, but no miscentering, with different fit ranges'''

    mxxlsnap=54

    configtemplate = 'general-{mc}-r{r}-xrayNONE-n2_4-nov2016'
    radialranges = [19, 6, 10]
    mcs = ['c4', 'diemer15', 'duffy']
    radiallabels = ['0.1-2.5 Mpc', '0.5-2.5 Mpc', '0.75-3.0 Mpc']
    labels = ['c=4', 'Diemer15', 'Duffy08']
    xoffsets = [0.98, 1.0, 1.02]


    for curr, r in enumerate(radialranges):

        outputname = 'compare_nfw_mc_radial_r{}'.format(r)

        configs = [configtemplate.format(mc=mc, r=r) for mc in mcs]
        chaindirs = ['{}/rundlns/mxxlsnap{}/{}'.format(outputdir, mxxlsnap, config) for config in configs]


        compareSimPlot(outputname, chaindirs, labels, xoffsets, metalabel = radiallabels[curr])



#############

def compareMCRelation_Redshift(outputdir):
    '''Compare bias levels using different MC relations, but no miscentering, with different fit ranges'''

    mxxlsnaps=[54, 41]

    configtemplate = 'general-{mc}-r{r}-xrayNONE-n2_4-nov2016'
    radialrange = 6
    mcs = ['c4', 'diemer15', 'duffy']
    redshiftlabels = ['z=0.25', 'z=1.0']
    mclabels = ['c=4', 'Diemer15', 'Duffy08']
    xoffsets = [0.99, 1.01]

    for curmc_index, curmc in enumerate(mcs):

        outputname = 'compare_nfw_{mc}_redshift'.format(mc = curmc)

        config = configtemplate.format(mc=curmc, r=radialrange)
        
        chaindirs = ['{}/rundlns/mxxlsnap{}/{}'.format(outputdir, mxxlsnap, config) for mxxlsnap in mxxlsnaps]


        compareSimPlot(outputname, chaindirs, redshiftlabels, xoffsets, metalabel = mclabels[curmc_index])


#############

def compareMCRelation_Cosmo():
    '''Compare bias levels using different MC relations, but no miscentering, with different cosmologies'''
    
    snaps = ['mxxlsnap54', 'bk11snap141']

    configtemplate = 'general-{mc}-r{r}-xrayNONE-n2_4-nov2016'
    radialrange = 6
    mcs = ['c4', 'diemer15', 'duffy']
    cosmolabels = ['MXXL', 'BK11']
    mclabels = ['c=4', 'Diemer15', 'Duffy08']
    xoffsets = [0.99, 1.01]

    for curmc_index, curmc in enumerate(mcs):

        outputname = 'compare_nfw_{mc}_cosmo'.format(mc = curmc)

        config = configtemplate.format(mc=curmc, r=radialrange)
        
        chaindirs = ['{}/rundlns/{}/{}'.format(outputdir, snap, config) for snap in snaps]


        compareSimPlot(outputname, chaindirs, cosmolabels, xoffsets, metalabel = mclabels[curmc_index])


###########

def compareMiscentering():
    '''Compare bias levels using different miscentering'''

    mxxlsnap=54

    configtemplate = 'general-diemer15-r6-{}-n2_4-nov2016'
    centers = ['xrayNONE', 'szmag', 'xraymag']
    labels = ['Perfect Centers', 'SZ Centers', 'X-ray Centers']
    xoffsets = [0.98, 1.0, 1.02]

    outputname = 'compare_nfw_centers'

    configs = [configtemplate.format(center) for center in centers]
    chaindirs = ['{}/rundlns/mxxlsnap{}/{}'.format(outputdir, mxxlsnap, config) for config in configs]


    compareSimPlot(outputname, chaindirs, labels, xoffsets)



#############

def compareMiscentering_SZRedshift():
    '''Compare bias levels using different miscentering'''

    mxxlsnaps=[54, 41]
    radialranges = [6, 19]
    configtemplate = 'general-diemer15-r{r}-szmag-n2_4-nov2016'
    redshiftlabels = ['z=0.25', 'z=1.0']
    radiallabels = ['0.5-2.5Mpc', '0.1-2.5 Mpc']
    xoffsets = [0.99, 1.01]

    outputname = 'compare_nfw_centers_szredshift'

    chaindirs = []
    for mxxlsnap in mxxlsnaps:
        majorvar = []
        for r in radialranges:
            config = configtemplate.format(r=r)
            chaindir = '{}/rundlns/mxxlsnap{}/{}'.format(outputdir, mxxlsnap, config)
            majorvar.append(chaindir)
        chaindirs.append(majorvar)


    compare2DimSimPlot(outputname, chaindirs, [redshiftlabels, radiallabels], xoffsets, biasylim=(0.25, 1.1))



#############

def summarizeChains(chaindirs, binnum, delta):

    mus = []
    globalmassbinlow = None
    globalmassbinhigh = None

    chainfiles = [psd.gatherChainFiles(chaindir, delta, binnum = binnum)[0] \
                  for chaindir in chaindirs]

    assert(len(chainfiles) > 0)

    for chainfile in chainfiles:




        chain = load_chains.loadChains([chainfile], trim=True)

        print chainfile, len(chain['logmu'])
        if len(chain['logmu'][0,:]) < 5000:
            print 'Skipping'
            continue

        split = int((chain['logmu'].shape[1] + 1000)/2.)
        splitlen = split - 1000
        c1mean = np.mean(chain['logmu'][0,1000:split])
        c1err = np.std(chain['logmu'][0,1000:split]) / np.sqrt(splitlen)
        c2mean = np.mean(chain['logmu'][0,split:])
        c2err = np.std(chain['logmu'][0,split:]) / np.sqrt(splitlen)
#        assert(np.abs(c1mean - c2mean)/np.sqrt(c1err**2 + c2err**2) < 5.)


        massbinlow, massbinhigh = [x[0] for x in readtxtfile.readtxtfile('%s.massrange' % chainfile)]

        if globalmassbinlow is None:
            globalmassbinlow = massbinlow
            globalmassbinhigh = massbinhigh

        assert(massbinlow == globalmassbinlow and massbinhigh == globalmassbinhigh)


        mu, muerr = ci.maxDensityConfidenceRegion(np.exp(chain['logmu'][0,1000::3]))

        mus.append(mu)


    return np.array(mus)


########

def MCSensitivityVsRadius(chainbase, massbin, radii, mcuncert = 0.2, delta = 500):

    configs = []
    for cur_radii in radii:
        for concen in [3,4,5]:
            configs.append('{}/general-c{}-r{}-xrayNONE-n2_4-nov2016'.format(chainbase,
                                                                             concen,
                                                                             cur_radii))

    configs = np.array(configs)

    bias = summarizeChains(configs, massbin, delta).reshape((len(radii), 3))

    print bias

    derivative = (bias[:,2] - bias[:,0])/2.

    frac_mass_err = mcuncert*np.abs(derivative)/bias[:,1]

    return frac_mass_err

###############

def MiscenteringSensitivityVsRadius(chainbase, massbin, radii, scalefactor = 0.5, delta = 500):

    configs = []
    for cur_radii in radii:
        for center in 'xrayNONE xraymag'.split():
            configs.append('{}/general-c4-r{}-{}-n2_4-nov2016'.format(chainbase,
                                                                      cur_radii,
                                                                      center))

    configs = np.array(configs)



    bias = summarizeChains(configs, massbin, delta).reshape((len(radii), 2))



    delta = (bias[:,1] - bias[:,0])

    frac_mass_err = scalefactor*np.abs(delta)/bias[:,0]

    return frac_mass_err

##########


def plotSensitivityvsInnerRadius(chainbase, outdir):

    figs = []

    deltas_massbins = [(200, (0, 7)), (500, (0, 6))]

    radii =  np.array([.1, .25, .5, .75])
    radii_ids = '19 3 6 9'.split()

    linestyles = ['--', ':', '-']
    colors = psd.c[0:2] + ['k']
    thicknesses = [1, 1, 3]
    labels = ['Mass-Concentration', 'Miscentering', 'Total']



    for delta, massbins in deltas_massbins:

        fig = pylab.figure()
        figs.append(fig)

        labelsApplied = False
        for massbin, color in zip(massbins, colors):

            
            mc_sensitivity = MCSensitivityVsRadius(chainbase, massbin, radii_ids, delta = delta)

            miscentering_sensitivity = MiscenteringSensitivityVsRadius(chainbase, massbin, radii_ids, delta = delta)

            total_sensitivity = np.sqrt(mc_sensitivity**2 + miscentering_sensitivity**2)

            sensitivities = [mc_sensitivity, miscentering_sensitivity, total_sensitivity]



            for sensitivity, linestyle, thickness, label in zip(sensitivities,
                                                                linestyles,
                                                                thicknesses,
                                                                labels):

                uselabel = None
                if not labelsApplied:
                    uselabel = label


                pylab.plot(radii, sensitivity, linestyle=linestyle,
                           color = color, linewidth = thickness, label = uselabel, marker = 'None')


            labelsApplied = True


        pylab.legend()
        pylab.xlabel('Inner Fit Radius [Mpc]', fontsize=16)
        pylab.ylabel('Fractional Systematic Uncertainty in $M_{{{delta}}}$'.format(delta = delta), fontsize=16)
        pylab.tight_layout()
        
        filebase = '{}/deltab_v_radius_{}'.format(outdir, delta)
        pylab.savefig('{}.png'.format(filebase))
        pylab.savefig('{}.pdf'.format(filebase))
        pylab.savefig('{}.ps'.format(filebase))
        pylab.savefig('{}.eps'.format(filebase))

    return figs

                                        

##########


def plotSensitivityvsOuterRadius(chainbase, outdir):

    figs = []

    deltas_massbins = [(200, (0, 7)), (500, (0, 6))]

    radii =  np.array([1.5, 2.0, 2.5, 3.0])
    radii_ids = '5 20 6 7'.split()

    linestyles = ['--', ':', '-']
    colors = psd.c[0:2] + ['k']
    thicknesses = [1, 1, 3]
    labels = ['Mass-Concentration', 'Miscentering', 'Total']



    for delta, massbins in deltas_massbins:

        fig = pylab.figure()
        figs.append(fig)

        labelsApplied = False
        for massbin, color in zip(massbins, colors):

            
            mc_sensitivity = MCSensitivityVsRadius(chainbase, massbin, radii_ids, delta = delta)

            miscentering_sensitivity = MiscenteringSensitivityVsRadius(chainbase, massbin, radii_ids, delta = delta)

            total_sensitivity = np.sqrt(mc_sensitivity**2 + miscentering_sensitivity**2)

            sensitivities = [mc_sensitivity, miscentering_sensitivity, total_sensitivity]



            for sensitivity, linestyle, thickness, label in zip(sensitivities,
                                                                linestyles,
                                                                thicknesses,
                                                                labels):

                uselabel = None
                if not labelsApplied:
                    uselabel = label


                pylab.plot(radii, sensitivity, linestyle=linestyle,
                           color = color, linewidth = thickness, label = uselabel, marker = 'None')


            labelsApplied = True


        ax = pylab.gca()
        ax.set_ylim(0.0, 0.07)
        pylab.legend(loc='upper left', ncol=3)
        pylab.xlabel('Outer Fit Radius [Mpc]', fontsize=16)
        pylab.ylabel('Fractional Systematic Uncertainty in $M_{{{delta}}}$'.format(delta = delta), fontsize=16)
        pylab.tight_layout()
        
        filebase = '{}/deltab_v_outerradius_{}'.format(outdir, delta)
        pylab.savefig('{}.png'.format(filebase))
        pylab.savefig('{}.pdf'.format(filebase))
        pylab.savefig('{}.ps'.format(filebase))
        pylab.savefig('{}.eps'.format(filebase))

    return figs

                                        

    
def compareACSMiscentering(chainoutdir):
    '''Compare bias levels using different miscentering'''

    mxxlsnap=41

    configtemplate = 'acs-diemer15-r_run26-{}-n2_4-aug2017'  
    centers = ['xraymagneticum', 'szmagneticum_ignorecore', 'core_none']
    labels = ['X-ray Centers', 'SZ Centers', 'Perfect Centers',  ]
    xoffsets = [0.98, 1.0, 1.02]

    outputname = 'compare_acsnfw_centers'

    configs = [configtemplate.format(center) for center in centers]
    chaindirs = ['{}/rundlns/{}'.format(chainoutdir, config) for config in configs]
    print chaindirs

    compareSimPlot(outputname, chaindirs, labels, xoffsets, deltas=[200])



#############

def compareACSconcentration(chainoutdir):
    '''Compare bias levels using different M-c assumptions'''

    mxxlsnap=41

    configtemplate = 'acs-{}-r_run26-core_none-n2_4-aug2017'  
    concentration = ['c3', 'c4', 'c5', 'diemer15']
    labels = concentration
    xoffsets = [0.98, 1.0, 1.02, 1.04]

    outputname = 'compare_acsnfw_concentration_perfectcenter'

    configs = [configtemplate.format(c) for c in concentration]
    chaindirs = ['{}/rundlns/{}'.format(chainoutdir, config) for config in configs]
    print chaindirs

    compareSimPlot(outputname, chaindirs, labels, xoffsets, deltas=[200])



#############
def compareACStestmassconcentrationfits(chainoutdir):
    '''Compare bias levels with fitting concentration'''
    #acs-cfree-r_run26-core_none-n2_4-samplemcmc-aug2017/
    
    mxxlsnap=41

    configtemplate = 'acs-{}-r_run26-core_none-n2_4-{}aug2017'  
    concentration = ['c3', 'c4', 'c5', 'diemer15', 'cfree']
    #concentration = ['cfree']
    chaintype = ['','','','','samplemcmc-']
    #chaintype = ['samplemcmc-']
    labels = concentration
    xoffsets = [0.96, 0.98, 1.0, 1.02, 1.04]
    #xoffsets = [1.0]
    outputname = 'compare_acsnfw_concentration_fitting_perfectcenter'

    configs = [configtemplate.format(c, ct) for c,ct in zip(concentration,chaintype)]
    chaindirs = ['{}/rundlns/{}'.format(chainoutdir, config) for config in configs]

    compareSimPlot(outputname, chaindirs, labels, xoffsets, deltas=[200])



#############
def compareACSjustDiemer(chainoutdir):
    '''just the diemer fit for testing'''
    # acs-diemer15-r_run26-core_none-n2_4-aug2017
    
    mxxlsnap=41

    configtemplate = 'acs-{}-r_run26-core_none-n2_4-{}aug2017'  
    #concentration = ['c3', 'c4', 'c5', 'diemer15', 'cfree']
    concentration = ['cfree','diemer15']
    #chaintype = ['','','','','samplemcmc-']
    chaintype = ['samplemcmc-','']
    labels = concentration
    #xoffsets = [0.96, 0.98, 1.0, 1.02, 1.04]
    xoffsets = [1.0,1.02]
    outputname = 'compare_acsnfw_Diemer_cfree'

    configs = [configtemplate.format(c, ct) for c,ct in zip(concentration,chaintype)]
    chaindirs = ['{}/rundlns/{}'.format(chainoutdir, config) for config in configs]

    compareSimPlot(outputname, chaindirs, labels, xoffsets, deltas=[200])
#############
def compareACSvsA10perfectcenters(chainoutdir):
    '''Check if bias changes with fit size'''
    # acs-diemer15-r_run26-core_none-n2_4-aug2017
    
    mxxlsnap=54 # Redshift 0.25 to first check
    #xoffsets = [0.96, 0.98, 1.0, 1.02, 1.04]
    xoffsets = [1.0,1.02]
    outputname = 'compare_perfect_centers_fitrange_cfree'

    configs = ['acs-cfree-rACS-core_none-n2_4-samplemcmc-aug2017','acs-cfree-r10-core_none-n2_4-samplemcmc-aug2017']
    labels = ['r=0.25-0.8 Mpc','r=0.75-3 Mpc']
    chaindirs = ['{}/rundlns/{}'.format(chainoutdir, config) for config in configs]

    compareSimPlot(outputname, chaindirs, labels, xoffsets, deltas=[200,500])

