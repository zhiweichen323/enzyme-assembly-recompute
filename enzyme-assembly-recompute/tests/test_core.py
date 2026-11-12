import sys
import unittest
from pathlib import Path
import numpy as np
from scipy.special import expit
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mlo_core import (loss_and_grad, fit_and_predict, crossval_predictions, auc_score,
                      roc_points, load_data, FEATURES, bootstrap_fixed_oof,
                      aggregate_pathways, bh_adjust)

SETTINGS = {'lambda': 1., 'max_iter': 2000, 'ftol': 1e-8, 'gtol': 1e-5}


class ScientificChecks(unittest.TestCase):
    def test_gradient_against_central_difference(self):
        X = np.array([[1,.5,-.2],[1,-1,.6],[1,.3,1.2]], dtype=float)
        y = np.array([1.,0.,1.]); w = np.array([.1,-.4,.7]); h=1e-6
        _, grad = loss_and_grad(w, X, y, 1.)
        numeric = np.array([(loss_and_grad(w+np.eye(3)[j]*h,X,y,1.)[0]-loss_and_grad(w-np.eye(3)[j]*h,X,y,1.)[0])/(2*h) for j in range(3)])
        np.testing.assert_allclose(grad, numeric, atol=1e-8, rtol=1e-7)

    def test_intercept_not_penalized_and_constant_features(self):
        pred, model = fit_and_predict(np.zeros((4,2)), np.array([1,0,0,0]), np.zeros((1,2)), SETTINGS)
        self.assertAlmostEqual(pred[0], .25, places=5)
        np.testing.assert_allclose(model['weights'], [0,0], atol=1e-10)

    def test_auc_independent_pairwise_and_ties(self):
        y=np.array([1,1,0,0])
        for p, expected in [(np.array([.9,.6,.7,.2]),.75),(np.array([.9,.6,.6,.2]),.875),(np.ones(4),.5)]:
            direct=np.mean([1. if a>b else (.5 if a==b else 0.) for a in p[y==1] for b in p[y==0]])
            self.assertEqual(auc_score(y,p),expected)
            self.assertEqual(auc_score(y,p),direct)
            x,z=roc_points(y,p)
            area=sum((x[i+1]-x[i])*(z[i]+z[i+1])/2 for i in range(len(x)-1))
            self.assertAlmostEqual(area,expected)

    def test_heldout_value_excluded_from_scaler_and_fitting(self):
        X=np.array([[1000.],[1.],[2.],[3.],[4.],[5.]])
        y=np.array([1,0,1,0,1,0])
        scores,models=crossval_predictions(X,y,SETTINGS,keep_models=True)
        self.assertEqual(models[0]['mean'][0],3.)
        for m in models:
            self.assertFalse(set(m['test_indices']) & set(m['train_indices']))
            tx=np.array(m['test_raw_features'])
            reconstructed=expit(m['intercept']+((tx-np.array(m['mean']))/np.array(m['scale']))@np.array(m['weights']))
            np.testing.assert_allclose(reconstructed,scores[m['test_indices']],atol=1e-14)

    def test_whole_pathway_excluded(self):
        groups=np.array(['A','A','B','B','C','C','D','D'])
        X=np.arange(16,dtype=float).reshape(8,2)
        y=np.array([1,1,0,0,1,1,0,0])
        p,models=crossval_predictions(X,y,SETTINGS,groups,True)
        self.assertEqual(len(models),4)
        for m in models:
            self.assertFalse(set(groups[m['test_indices']]) & set(groups[m['train_indices']]))
        gx,gy,names=aggregate_pathways(X,y,groups)
        self.assertEqual(gx.shape,(4,5))
        self.assertEqual(names,['A','B','C','D'])

    def test_bootstrap_seed_and_bounds(self):
        y=np.array([1,1,0,0]); p=np.array([.9,.6,.7,.2])
        a=bootstrap_fixed_oof(y,p,30,42)
        np.testing.assert_array_equal(a,bootstrap_fixed_oof(y,p,30,42))
        self.assertTrue(np.all((a>=0)&(a<=1)))

    def test_bh_known_values(self):
        np.testing.assert_allclose(bh_adjust([.01,.04,.03]),[.03,.04,.04])

    def test_provided_input(self):
        root=Path(__file__).resolve().parents[1]
        rows,X,y,g=load_data(root/'data'/'analysis_input_100.csv')
        self.assertEqual(X.shape,(100,14))
        self.assertEqual(int(y.sum()),39)
        self.assertEqual(len(set(g)),25)
        self.assertEqual(len(FEATURES),14)

    def test_single_class_auc_rejected(self):
        with self.assertRaises(ValueError): auc_score(np.array([1]),np.array([.5]))


if __name__=='__main__':
    unittest.main()
