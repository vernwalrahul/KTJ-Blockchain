'''
Populates the required pdf form templates: both for individual certificates and for the hash index.
'''
import os
import sys
import glob
import json
import configargparse
from pdfrw import PdfReader, PdfWriter, PdfDict
from blockchain_proofs import ChainPointV2
from blockchain_certificates import pdf_utils
from blockchain_certificates import publish_hash


'''
Inserts the ChainPointV2 proof as pdf metadata for each certificate. Metadata
key is "chainpoint_proof"
'''
def insert_proof_to_certificates(conf, cp, txid, cert_files):
    print('')
    for ind, val in enumerate(cert_files):
        proof = json.dumps( cp.get_receipt(ind, txid) )
        metadata = PdfDict(chainpoint_proof=proof)
        pdf = PdfReader(val)
        pdf.Info.update(metadata)
        PdfWriter().write(val, pdf)
        # print progress
        print('.', end="", flush=True)


'''
Creates a new ChainPointV2 object initializes with the certificates passed and
creates the corresponding merkle tree
'''
def prepare_chainpoint_tree(hashes):
    cp = ChainPointV2()
    cp.add_leaf(hashes)
    cp.make_tree()
    return cp


'''
Loads and returns the configuration options (either from --config or from
specifying the specific options.
'''
def load_config():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    default_config = os.path.join(base_dir, 'config.ini')
    p = configargparse.getArgumentParser(default_config_files=[default_config])
    p.add('-c', '--config', required=False, is_config_file=True, help='config file path')
    p.add_argument('-d', '--working_directory', type=str, default='.', help='the main working directory - all paths/files are relative to this')
    p.add_argument('-i', '--pdf_cert_template_file', type=str, default='cert_template.pdf', help='the pdf certificate form to populate')
    p.add_argument('-s', '--issuer', type=str, help='the name of the institution to (added in certificate metadata)')
    p.add_argument('-a', '--issuing_address', type=str, help='the issuing address with enough funds for the transaction; assumed to be imported in local node wallet')
    p.add_argument('-v', '--graduates_csv_file', type=str, default='graduates.csv', help='the csv file with the graduate data')
    p.add_argument('-e', '--certificates_directory', type=str, default='certificates', help='the directory where the new certificates will be copied')
    p.add_argument('-g', '--certificates_global_fields', type=str, default='', help='certificates global fields expressed as JSON string')
    p.add_argument('-f', '--cert_names_csv_column', type=str, default='name', help='use this column from csv file for naming the certificates')
    p.add_argument('-m', '--cert_metadata_columns', type=str, default='name,degree,grade', help='the specified columns from the csv or global fields will be included as json metadata')
    p.add_argument('-n', '--full_node_url', type=str, default='127.0.0.1:18332', help='the url of the full node to use')
    p.add_argument('-u', '--full_node_rpc_user', type=str, help='the rpc user as specified in the node\'s configuration')
    p.add_argument('-t', '--testnet', action='store_true', help='specify if testnet or mainnet will be used')
    p.add_argument('-f', '--tx_fee_per_byte', type=int, default=100, help='the fee per transaction byte in satoshis')
    p.add_argument('-p', '--hash_prefix', type=str, help='prepend the hash that we wish to issue with this hexadecimal')
    args, _ = p.parse_known_args()
    return args


def main():
    if sys.version_info.major < 3:
        sys.stderr.write('Python 3 is required!')
        sys.exit(1)

    conf = load_config()
    print(conf)
    pdf_utils.populate_pdf_certificates(conf)

    # get certificate file list here (to ensure it is identical to both
    # 'hash_certificates' and 'insert_proof_to_certificates'
    certificates_directory = os.path.join(conf.working_directory, conf.certificates_directory)
    cert_files = glob.glob(certificates_directory + os.path.sep + "*.pdf")

    cert_hashes = pdf_utils.hash_certificates(cert_files)
    cp = prepare_chainpoint_tree(cert_hashes)
    txid = publish_hash.issue_hash(conf, True, cp.get_merkle_root())
    insert_proof_to_certificates(conf, cp, txid, cert_files)
    print('\nTx hash: {}'.format(txid))


if __name__ == "__main__":
    main()
