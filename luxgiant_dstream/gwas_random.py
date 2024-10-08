"""
Module to perform a GWAS analysis using a random effect model.
"""

import os
import pandas as pd

from luxgiant_dstream.Helpers import shell_do, delete_temp_files
from luxgiant_dstream.plots import manhattan_plot, qq_plot
from luxgiant_dstream.annotate_tools import get_variant_context

class GWASrandom:

    def __init__(self, input_path:str, input_name:str, output_path:str, output_name:str, config_dict:str, preps_path:str) -> None:

        """
        Initialize the GWASrandom class.

        Parameters:
        -----------
        input_path : str
            Path to the input data.
        input_name : str
            Name of the input data.
        output_path : str
            Path to the output data.
        output_name : str
            Name of the output data.
        config_dict : dict
            Dictionary containing the configuration parameters.
        preps_path : str
            Path to the preparatory data.

        Returns:
        --------
        None
        """
        
        # check if paths are set
        if input_path is None or output_path is None:
            raise ValueError("Values for input_path, output_path and dependables_path must be set upon initialization.")

        self.input_path  = input_path
        self.output_path = output_path
        self.input_name  = input_name
        self.output_name = output_name
        self.config_dict = config_dict
        self.preps_path  = preps_path

        self.files_to_keep = []

        # create results folder
        self.results_dir = os.path.join(output_path, 'gwas_random')
        if not os.path.exists(self.results_dir):
            os.mkdir(self.results_dir)

        # create figures folder
        self.plots_dir = os.path.join(output_path, 'plots_random')
        if not os.path.exists(self.plots_dir):
            os.mkdir(self.plots_dir)

        print("\033[1;32mAnalysis of GWAS data using a random effect model initialized.\033[0m")

        pass

    def prepare_aux_files(self)->dict:

        """
        Prepare auxiliary files for the GWAS analysis.
        """
        
        input_path  = self.input_path
        input_name  = self.input_name
        results_dir = self.results_dir
        output_name = self.output_name

        step = "prepare_aux_files"

        df_fam = pd.read_csv(os.path.join(input_path, input_name+'.fam'), sep=' ', header=None)

        df_pheno = df_fam[[df_fam.columns[0], df_fam.columns[1], df_fam.columns[5]]].copy()

        # recode phenotype
        df_pheno[5] = df_pheno[5]-1

        df_pheno.to_csv(os.path.join(results_dir, output_name+'_pheno.phen'), sep='\t', header=False, index=False)

        # recode sex
        df_sex = df_fam[[0,1,4]].copy()

        df_sex.to_csv(os.path.join(results_dir, output_name+'_sex.covar'), sep='\t', header=False, index=False)

        # report
        process_complete = True

        outfiles_dict = {
            'python_out': results_dir
        }

        out_dict = {
            'pass': process_complete,
            'step': step,
            'output': outfiles_dict
        }

        return out_dict
    
    def compute_grm(self)->dict:

        """
        Compute the genetic relationship matrix (GRM) for the GWAS analysis using GCTA.
        """

        results_dir= self.results_dir
        prep_path  = self.preps_path
        output_name= self.output_name

        step = "compute_grm"

        # compute the number of threads to use
        if os.cpu_count() is not None:
            max_threads = os.cpu_count()-2
        else:
            max_threads = 10

        # gcta commands
        gcta_cmd1 = f"gcta64 --bfile {os.path.join(prep_path, output_name+'_LDpruned')} --make-grm --thread-num {max_threads} --out {os.path.join(results_dir, output_name+'_grm')}"

        gcta_cmd2 = f"gcta64 --grm {os.path.join(results_dir, output_name+'_grm')} --make-bK-sparse 0.05 --out {os.path.join(results_dir, output_name+'_sparse')}"

        # run gcta commands
        cmds = [gcta_cmd1, gcta_cmd2]
        for cmd in cmds:
            shell_do(cmd, log=True)

        # report
        process_complete = True

        outfiles_dict = {
            'gcta_out': results_dir
        }

        out_dict = {
            'pass': process_complete,
            'step': step,
            'output': outfiles_dict
        }

        return out_dict
    
    def run_gwas_random(self)->dict:

        """
        Method to run the GWAS analysis using a random effect model.
        """

        results_dir = self.results_dir
        input_name  = self.input_name
        input_path  = self.input_path
        output_name = self.output_name
        config_dict = self.config_dict
        preps_path  = self.preps_path

        maf = config_dict['maf']

        step = "run_gwas_random"

        # compute the number of threads to use
        if os.cpu_count() is not None:
            max_threads = os.cpu_count()-2
        else:
            max_threads = 10

        # gcta command
        gcta_cmd = f"gcta64 --bfile {os.path.join(input_path, input_name)} --fastGWA-mlm-binary --maf {maf}  --grm-sparse {os.path.join(results_dir, output_name+'_sparse')} --qcovar {os.path.join(preps_path, output_name+'_pca.eigenvec')} --covar {os.path.join(results_dir, output_name+'_sex.covar')} --pheno {os.path.join(results_dir, output_name+'_pheno.phen')} --out {os.path.join(results_dir,output_name+'_assocSparseCovar_pca_sex-mlm-binary')}--thread-num {max_threads}"

        # run gcta command
        shell_do(gcta_cmd, log=True)

        # rename columns for later use with GCTA
        df = pd.read_csv(os.path.join(results_dir, output_name+'_assocSparseCovar_pca_sex-mlm-binary--thread-num.fastGWA'), sep="\t")
        rename = {
            'CHR'     :'CHR',	
            'SNP'     :'SNP',
            'POS'     :'POS',	
            'A1'      :'A1', 
            'A2'      :'A2', 
            'N'       :'N', 
            'AF1'     :'freq', 
            'T'       :'T', 
            'SE_T'    :'SE_T', 
            'P_noSPA' :'P_noSPA',
            'BETA'    :'b', 
            'SE'      :'se', 
            'P'       :'p', 
            'CONVERGE':'CONVERGE'
        }
        df = df.rename(columns=rename)
        df.to_csv(os.path.join(results_dir, output_name+'_assocSparseCovar_pca_sex-mlm-binary--thread-num.fastGWA'), sep="\t", index=False)

        self.files_to_keep.append(output_name+'_assocSparseCovar_pca_sex-mlm-binary--thread-num.fastGWA')

        # report
        process_complete = True

        outfiles_dict = {
            'gcta_out': results_dir
        }

        out_dict = {
            'pass': process_complete,
            'step': step,
            'output': outfiles_dict
        }

        return out_dict
    
    def get_top_hits(self)->dict:

        """
        Method to extract the top hits from the GWAS analysis.
        """

        results_dir = self.results_dir
        input_name  = self.input_name
        input_path  = self.input_path
        output_name = self.output_name

        maf = self.config_dict['maf']

        step = "get_top_hits"

        # compute the number of threads to use
        if os.cpu_count() is not None:
            max_threads = os.cpu_count()-2
        else:
            max_threads = 10

        # load results of association analysis
        df = pd.read_csv(os.path.join(results_dir, output_name+'_assocSparseCovar_pca_sex-mlm-binary--thread-num.fastGWA'), sep="\t")

        # prepare .ma file
        df = df[['SNP', 'A1', 'A2', 'freq', 'b', 'se', 'p', 'N']].copy()

        df.to_csv(os.path.join(results_dir, 'cojo_file.ma'), sep="\t", index=False)

        del df

        # gcta command
        gcta_cmd = f"gcta64 --bfile {os.path.join(input_path, input_name)} --maf {maf} --cojo-slct --cojo-file {os.path.join(results_dir, 'cojo_file.ma')}   --out {os.path.join(results_dir, output_name+'_assocSparseCovar_pca_sex-mlm-binary-cojo')} --thread-num {max_threads}"

        # execute gcta command
        shell_do(gcta_cmd, log=True)

        self.files_to_keep.append(output_name+'_assocSparseCovar_pca_sex-mlm-binary-cojo.jma.cojo')
        self.files_to_keep.append(output_name+'_assocSparseCovar_pca_sex-mlm-binary-cojo.ldr.cojo')

        # report
        process_complete = True

        outfiles_dict = {
            'plink_out': results_dir
        }

        out_dict = {
            'pass': process_complete,
            'step': step,
            'output': outfiles_dict
        }

        return out_dict

    def annotate_top_hits(self)->dict:

        """
        Annotate the top hits from the association analysis.
        """

        import time

        results_dir = self.results_dir
        output_name = self.output_name

        step = "annotate_hits"

        # load the data
        cojo_file_path = os.path.join(results_dir, output_name+'_assocSparseCovar_pca_sex-mlm-binary-cojo.jma.cojo')

        # check if .jma file exists
        if os.path.exists(cojo_file_path):
            df_hits = pd.read_csv(cojo_file_path, sep="\t")
        else:
            FileExistsError("File cojo_file.jma not found in the results directory.")

        df_hits = df_hits[['Chr', 'SNP', 'bp']].copy()

        for k in range(df_hits.shape[0]):
            # get variant context
            chr = df_hits.loc[k, 'Chr']
            pos = df_hits.loc[k, 'bp']

            context = get_variant_context(chr, pos)

            if context is None:
                context = 'NA'
            df_hits.loc[k, 'GENE'] = context[0]

            time.sleep(1.5)

        df_hits = df_hits[['SNP', 'GENE']].copy()

        # save the annotated data
        df_hits.to_csv(os.path.join(results_dir, 'snps_annotated.csv'), sep="\t", index=False)

        self.files_to_keep.append('snps_annotated.csv')

        # report
        process_complete = True

        outfiles_dict = {
            'plink_out': results_dir
        }

        out_dict = {
            'pass': process_complete,
            'step': step,
            'output': outfiles_dict
        }
        
        return out_dict
    
    def plot_drawings(self)->dict:

        """
        Method to draw Manhattan plot and QQ plot for the GWAS analysis.
        """

        plots_dir  = self.plots_dir
        results_dir= self.results_dir
        output_name= self.output_name

        annotate = self.config_dict['annotate']

        step = "draw_plots"

        # load GWAS results
        df_gwas = pd.read_csv(
            os.path.join(results_dir, output_name+'_assocSparseCovar_pca_sex-mlm-binary--thread-num.fastGWA'), 
            sep="\t",
            usecols=['SNP', 'CHR', 'p']
        )

        # draw Manhattan plot
        if annotate:
            df_annot = pd.read_csv(os.path.join(results_dir, "snps_annotated.csv"), sep="\t")

            mann_plot = manhattan_plot(
                df_gwas    =df_gwas,
                df_annot   =df_annot,
                plots_dir  =plots_dir,
                annotate   =True
            )
        else:
            mann_plot = manhattan_plot(
                df_gwas    =df_gwas,
                df_annot   =df_annot,
                plots_dir  =plots_dir,
                annotate   =False
            )

        # draw QQ plot
        QQ_plot = qq_plot(df_gwas, plots_dir)

        #delete_temp_files(self.files_to_keep, results_dir)

        # report
        process_complete = (mann_plot & QQ_plot)

        outfiles_dict = {
            'plink_out': plots_dir
        }

        out_dict = {
            'pass': process_complete,
            'step': step,
            'output': outfiles_dict
        }
        
        return out_dict
